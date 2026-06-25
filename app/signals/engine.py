"""
Main signal engine — orchestrates analysis, scoring, filtering, and signal generation.
This is the brain of the system.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, func

from app.config import settings
from app.database import async_session
from app.models import Signal, SignalDirection, SignalStatus, Tier
from app.exchanges.manager import exchange_manager
from app.exchanges.scoring import exchange_scorer
from app.signals.analyzer import candles_to_df, compute_indicators, detect_patterns, analyze_trend
from app.signals.correlation import analyze_cross_exchange_correlation, compute_btc_correlation
from app.signals.filters import signal_filter
from app.signals.scoring import compute_signal_score
from app.ml.features import extract_features, detect_volume_anomaly
from app.ml.quality_gate import quality_gate

import pandas as pd
from app.signals.analyzer import IndicatorSet


class SignalEngine:
    """Main signal generation engine."""

    # Dynamic parameters — strict quality filtering
    MIN_CONFIDENCE = 0.72  # Raised from 0.65 — quality over quantity
    TIMEFRAMES = ["4h", "1h", "30m", "15m"]  # Multi-TF: longer for longs, shorter for shorts
    MAX_ACTIVE_SIGNALS = 15  # Reduced from 20 — fewer but higher quality signals
    COIN_COOLDOWN_HOURS = 4  # Enough to prevent spam, not so long that system feels dead

    async def scan_all_pairs(self) -> list[Signal]:
        """Full market scan — the main entry point for signal generation."""
        generated_signals = []

        # Check active signal count
        async with async_session() as session:
            active_count = await session.scalar(
                select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
            )
            if active_count >= self.MAX_ACTIVE_SIGNALS:
                logger.info(f"Max active signals reached ({active_count}), skipping scan")
                return []

            # Get coins with active signals OR recent signals (cooldown) from DB
            cooldown_cutoff = datetime.now(timezone.utc) - timedelta(hours=self.COIN_COOLDOWN_HOURS)
            active_coins_result = await session.execute(
                select(Signal.coin_symbol).where(
                    (Signal.status == SignalStatus.ACTIVE) |
                    (Signal.created_at >= cooldown_cutoff)
                ).distinct()
            )
            blocked_coins = {row[0] for row in active_coins_result.all()}

        # Also check Redis cooldowns (faster, survives restarts)
        from app.redis_client import is_on_cooldown
        # Redis cooldowns are checked per-pair in _analyze_pair

        # Get top coins by volume across exchanges
        top_pairs = await self._get_scannable_pairs()
        if not top_pairs:
            logger.warning("No scannable pairs returned from exchanges — check exchange connectivity")
            return []

        # Filter out coins that already have active/recent signals
        scannable = [p for p in top_pairs if p["symbol"].replace("USDT", "") not in blocked_coins]
        skipped = len(top_pairs) - len(scannable)
        if skipped:
            logger.debug(f"Skipped {skipped} pairs (active/cooldown)")
        logger.info(f"Scanning {len(scannable)} pairs (from {len(top_pairs)} candidates, {len(blocked_coins)} on cooldown)...")

        for pair_info in scannable:
            try:
                signal = await self._analyze_pair(pair_info)
                if signal:
                    generated_signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair_info.get('symbol')}: {e}")

        logger.info(f"Scan complete: {len(generated_signals)} signals generated")
        return generated_signals

    async def _get_scannable_pairs(self) -> list[dict]:
        """Get top pairs across exchanges, ranked by volume and activity.
        Also updates exchange scoring from ticker data."""
        all_tickers = {}
        exchanges_ok = 0

        for name, exchange in exchange_manager.exchanges.items():
            try:
                tickers = await exchange.get_all_tickers()
                if tickers:
                    exchanges_ok += 1
                    exchange_scorer.record_call(name, success=True)
                    logger.debug(f"  {name}: {len(tickers)} pairs")

                    # Update scoring from first BTCUSDT ticker found
                    for t in tickers:
                        if t.symbol == "BTCUSDT":
                            exchange_scorer.update_liquidity_from_ticker(name, t)
                            if t.timestamp:
                                exchange_scorer.update_freshness(name, t.timestamp.timestamp())
                            break

                    # Update latency from CCXT exchange if available
                    if hasattr(exchange, "avg_latency_ms"):
                        exchange_scorer.update_latency(name, exchange.avg_latency_ms)

                    for t in tickers:
                        symbol = t.symbol
                        if symbol not in all_tickers:
                            all_tickers[symbol] = {
                                "symbol": symbol,
                                "exchanges": [],
                                "total_volume": 0,
                                "price": t.last_price,
                                "change_24h": t.price_change_pct_24h,
                            }
                        all_tickers[symbol]["exchanges"].append(name)
                        all_tickers[symbol]["total_volume"] += t.volume_24h
                else:
                    exchange_scorer.record_call(name, success=False)
                    logger.warning(f"  {name}: returned 0 tickers")
            except Exception as e:
                exchange_scorer.record_call(name, success=False)
                logger.error(f"Failed to get tickers from {name}: {e}")

        logger.info(f"Exchanges responding: {exchanges_ok}/{len(exchange_manager.exchanges)}, unique pairs: {len(all_tickers)}")

        # Filter: available on at least 2 exchanges, meaningful volume
        candidates = [
            p for p in all_tickers.values()
            if len(p["exchanges"]) >= 2 and p["total_volume"] > 50000
        ]

        # Sort exchanges within each pair by score (best first)
        for c in candidates:
            c["exchanges"] = exchange_scorer.get_ordered_list(c["exchanges"])

        # Sort by volume + volatility (higher abs change = more opportunity)
        candidates.sort(
            key=lambda x: x["total_volume"] * (1 + abs(x.get("change_24h", 0)) / 100),
            reverse=True,
        )

        return candidates[:100]  # Scan top 100

    async def _analyze_pair(self, pair_info: dict) -> Signal | None:
        """Deep analysis of a single pair — the core signal logic.
        Uses exchange scoring for best data source, with fallback across all available exchanges."""
        symbol = pair_info["symbol"]
        available_exchanges = pair_info["exchanges"]  # already sorted by score

        # 1. Get candles — try each exchange until we have enough timeframes
        candle_data: dict[str, list] = {}
        primary_exchange = available_exchanges[0]
        candle_source_exchange: str | None = None  # track which exchange actually provided data

        for ex_name in available_exchanges:
            exchange = exchange_manager.get_exchange(ex_name)
            for tf in self.TIMEFRAMES:
                if tf in candle_data:
                    continue  # Already fetched this timeframe
                try:
                    candles = await exchange.get_candles(symbol, tf, limit=200)
                    if len(candles) >= 50:
                        candle_data[tf] = candles
                        if candle_source_exchange is None:
                            candle_source_exchange = ex_name
                        exchange_scorer.record_call(ex_name, success=True)
                    else:
                        exchange_scorer.record_call(ex_name, success=True)
                except Exception as e:
                    exchange_scorer.record_call(ex_name, success=False)
                    logger.debug(f"Failed to get {tf} candles for {symbol} on {ex_name}: {e}")

            if len(candle_data) >= 2:
                break  # Enough data

        if candle_source_exchange:
            primary_exchange = candle_source_exchange

        if not candle_data:
            return None

        # Require at least 2 timeframes for reliable analysis
        if len(candle_data) < 2:
            logger.debug(f"Only {len(candle_data)} timeframe(s) for {symbol}, skipping (need 2)")
            return None

        # 2. Compute indicators for each timeframe
        analyses = {}
        for tf, candles in candle_data.items():
            df = candles_to_df(candles)
            indicators = compute_indicators(df)
            patterns = detect_patterns(df)
            trend = analyze_trend(df, tf)
            analyses[tf] = {
                "df": df,
                "indicators": indicators,
                "patterns": patterns,
                "trend": trend,
            }

        # 3. Determine signal direction from multi-timeframe analysis
        direction = self._determine_direction(analyses)
        if direction is None:
            return None

        # 4. Cross-exchange correlation
        correlation = await analyze_cross_exchange_correlation(symbol, "4h", 100)

        # 5. Use primary timeframe for signal levels
        primary_tf = "4h" if "4h" in analyses else list(analyses.keys())[0]
        primary = analyses[primary_tf]
        indicators = primary["indicators"]
        df = primary["df"]

        # 5a. Volume anomaly detection (scipy z-score)
        volume_history = df["volume"].tolist() if "volume" in df.columns else []
        is_volume_anomaly, volume_zscore = detect_volume_anomaly(volume_history, threshold=3.5)
        # Note: anomaly is logged but not used to reject — could be breakout or wash trading

        # 5b. Market regime detection
        from app.signals.regime import detect_regime
        regime_result = detect_regime(indicators)

        # 5c. Reject signals with missing critical indicators
        # Without these, analysis is unreliable — better to skip than guess with neutrals
        critical_missing = []
        if indicators.rsi_14 is None:
            critical_missing.append("RSI")
        if indicators.atr is None or indicators.atr <= 0:
            critical_missing.append("ATR")
        if indicators.adx is None:
            critical_missing.append("ADX")
        if indicators.volume_ratio is None:
            critical_missing.append("volume_ratio")
        if critical_missing:
            logger.debug(f"Signal for {symbol} skipped: missing critical indicators: {critical_missing}")
            return None

        # 6. Compute entry/exit levels (dynamic R:R based on regime)
        levels = self._compute_levels(indicators, direction, df, regime_result=regime_result)
        if levels is None:
            return None

        # 7. Apply quality filters — pass patterns, trends, and regime for new filters
        patterns_by_tf = {
            tf: [{"name": p.name, "direction": p.direction, "strength": p.strength} for p in a["patterns"]]
            for tf, a in analyses.items()
        }
        trend_by_tf = {tf: a["trend"].direction for tf, a in analyses.items()}

        filter_result = await signal_filter.apply_all_filters(
            df=df,
            indicators=indicators,
            direction=direction,
            volume_24h=pair_info.get("total_volume"),
            patterns_by_tf=patterns_by_tf,
            trend_by_tf=trend_by_tf,
            regime_direction=regime_result.regime.value,
            regime_strength=regime_result.strength,
        )

        if not filter_result.passed:
            logger.debug(f"Signal for {symbol} filtered out: {filter_result.warnings}")
            return None

        # 8. Compute confidence score
        score = compute_signal_score(
            indicators=indicators,
            trend=primary["trend"],
            patterns=primary["patterns"],
            correlation=correlation,
            direction=direction,
            entry_price=levels["entry"],
            stop_loss=levels["stop_loss"],
            tp1=levels["tp1"],
            tp2=levels.get("tp2"),
            tp3=levels.get("tp3"),
        )

        # Combine: signal score (65%) + filter quality (25%) + volume confirmation (10%)
        final_confidence = score.total * 0.65 + filter_result.score * 0.25 + score.volume_score * 0.10
        final_confidence = min(1.0, final_confidence)

        if final_confidence < self.MIN_CONFIDENCE:
            logger.debug(f"Signal for {symbol} below confidence threshold: {final_confidence:.2f}")
            return None

        # 9. ML quality gate — extract features and predict
        ex_score = exchange_scorer.get_score(primary_exchange).composite
        ml_features = extract_features(
            indicators=indicators,
            correlation=correlation,
            volume_history=volume_history,
            exchange_score=ex_score,
            direction=direction,
        )
        ml_prediction = quality_gate.predict(ml_features)

        # In active mode (not shadow), filter low-quality signals
        if not ml_prediction.shadow_mode and ml_prediction.p_tp1 < 0.35:
            logger.info(f"Signal for {symbol} rejected by ML gate: p_tp1={ml_prediction.p_tp1:.3f}")
            return None

        # 10. BTC correlation for context
        btc_corr = await compute_btc_correlation(symbol, "4h", 100)

        # 10a. DeepSeek AI gate — real AI analysis before signal creation
        ai_analysis = {}
        ai_reasoning_text = ""
        try:
            from app.ai.deepseek import deepseek as ds_client
            all_patterns_flat = []
            for tf, a in analyses.items():
                for p in a["patterns"]:
                    all_patterns_flat.append(f"{tf}: {p.name} ({p.direction})")

            ai_analysis = await ds_client.analyze_signal_context(
                coin_symbol=symbol.replace("USDT", ""),
                indicators=indicators.to_dict(),
                patterns=all_patterns_flat,
                trend_direction=direction,
                news_context=[],  # news_context populated by RAG below
                btc_correlation=btc_corr,
                fear_greed=None,
            )

            ds_adjustment = ai_analysis.get("confidence_adjustment", 0.0)
            # Clamp to ±0.2
            ds_adjustment = max(-0.2, min(0.2, ds_adjustment))
            # NOTE: Do NOT apply adjustment to confidence score.
            # DeepSeek has no training on our signal outcomes — applying unvalidated
            # adjustments adds noise, not signal. Keep for metadata/reasoning only.
            # final_confidence += ds_adjustment  # DISABLED — was causing random kills

            # If DeepSeek says strongly negative, log but do NOT reject
            if ds_adjustment <= -0.15:
                logger.info(f"DeepSeek flagged {symbol}: adj={ds_adjustment:.2f}, reason={ai_analysis.get('reasoning_en', '')[:100]} — noted (not filtering)")

            # Build multi-lang AI reasoning
            reasoning_parts = []
            if ai_analysis.get("reasoning_en"):
                reasoning_parts.append(ai_analysis["reasoning_en"])
            if ai_analysis.get("risk_factors"):
                reasoning_parts.append(f"Risks: {', '.join(ai_analysis['risk_factors'][:3])}")
            if ai_analysis.get("invalidation"):
                reasoning_parts.append(f"Invalidation: {ai_analysis['invalidation']}")
            ai_reasoning_text = " | ".join(reasoning_parts) if reasoning_parts else ""

        except Exception as e:
            logger.warning(f"DeepSeek AI gate failed for {symbol}: {e} — proceeding without AI gate")

        # 10b. RAG enrichment — retrieve similar historical signals
        rag_analysis = {}
        try:
            from app.ai.rag import rag_engine
            rag_analysis = await rag_engine.enrich_signal_analysis(
                coin_symbol=symbol.replace("USDT", ""),
                direction=direction,
                indicators=indicators.to_dict(),
                confidence=final_confidence,
            )
            rag_adjustment = rag_analysis.get("confidence_adjustment", 0.0)
            rag_adjustment = max(-0.12, min(0.12, rag_adjustment))
            # NOTE: Do NOT apply adjustment. RAG similarity matching doesn't validate
            # that past pattern outcomes predict future outcomes.
            # final_confidence += rag_adjustment  # DISABLED

            if rag_analysis.get("historical_context"):
                hist_ctx = rag_analysis["historical_context"]
                logger.debug(f"RAG context for {symbol}: {hist_ctx.get('similar_signals_found', 0)} similar signals, adj={rag_adjustment:.3f}")

        except Exception as e:
            logger.warning(f"RAG enrichment failed for {symbol}: {e} — proceeding without RAG")

        # Final confidence clamp and recheck threshold
        final_confidence = max(0.0, min(1.0, final_confidence))
        if final_confidence < self.MIN_CONFIDENCE:
            logger.debug(f"Signal for {symbol} below threshold after AI/RAG: {final_confidence:.3f}")
            return None

        # 11. Build factors dict
        factors = {
            "timeframes": list(analyses.keys()),
            "trend": {tf: a["trend"].direction for tf, a in analyses.items()},
            "patterns": {
                tf: [p.name for p in a["patterns"]]
                for tf, a in analyses.items() if a["patterns"]
            },
            "indicators": indicators.to_dict(),
            "correlation": {
                "price_correlation": correlation.price_correlation,
                "consensus": correlation.consensus_direction,
                "exchanges": correlation.exchanges_analyzed,
            },
            "btc_correlation": btc_corr,
            "filter_score": filter_result.score,
            "filter_warnings": filter_result.warnings,
            "score_breakdown": score.components,
            # ML gate metadata
            "ml_gate": {
                "p_tp1": round(ml_prediction.p_tp1, 4),
                "shadow_mode": ml_prediction.shadow_mode,
                "model_version": ml_prediction.model_version,
                "features_used": ml_prediction.features_used,
            },
            # Anomaly detection metadata
            "volume_anomaly": {
                "is_anomaly": is_volume_anomaly,
                "zscore": round(volume_zscore, 4),
            },
            # Exchange scoring metadata
            "exchange_score": {
                "primary": primary_exchange,
                "composite": round(ex_score, 4),
                "available": available_exchanges,
            },
            # Market regime metadata
            "regime": {
                "type": levels.get("regime"),
                "strength": levels.get("regime_strength"),
                "factors": levels.get("regime_factors", []),
                "multipliers": levels.get("multipliers"),
            },
            # DeepSeek AI gate metadata
            "ai_gate": {
                "confidence_adjustment": ai_analysis.get("confidence_adjustment", 0.0),
                "risk_factors": ai_analysis.get("risk_factors", []),
                "invalidation": ai_analysis.get("invalidation", ""),
                "recommended_timeframe": ai_analysis.get("recommended_timeframe", ""),
            },
            # RAG enrichment metadata
            "rag": {
                "confidence_adjustment": rag_analysis.get("confidence_adjustment", 0.0),
                "historical_context": rag_analysis.get("historical_context", {}),
            },
        }

        # 12. Determine minimum tier
        if final_confidence >= 0.80:
            min_tier = Tier.FREE  # High-confidence signals shown to everyone (as teaser)
        elif final_confidence >= 0.65:
            min_tier = Tier.PRO
        else:
            min_tier = Tier.ELITE

        # 13. Compute risk reward ratio for reasoning
        risk = abs(levels["entry"] - levels["stop_loss"])
        reward = abs(levels["tp1"] - levels["entry"])
        rr = round(reward / risk, 2) if risk > 0 else 0

        # 14. Extract coin info + logo from metadata
        base_symbol = symbol.replace("USDT", "")
        coin_name = base_symbol
        coin_logo_url = None
        try:
            from app.models import CoinMeta
            async with async_session() as _meta_session:
                meta = await _meta_session.scalar(
                    select(CoinMeta).where(CoinMeta.symbol == symbol)
                )
                if meta:
                    coin_name = meta.name or base_symbol
                    coin_logo_url = meta.logo_url
        except Exception:
            pass

        # 15. Save signal to DB
        entry = levels["entry"]
        atr = indicators.atr or 0
        entry_zone_pct = atr / entry * 0.5 if entry > 0 and atr > 0 else 0.005  # ±0.5 ATR zone or ±0.5%

        signal = Signal(
            coin_symbol=base_symbol,
            coin_name=coin_name,
            coin_logo_url=coin_logo_url,
            exchange=primary_exchange.capitalize(),
            pair=symbol,
            direction=SignalDirection.LONG if direction == "long" else SignalDirection.SHORT,
            timeframe=primary_tf,
            entry_price=entry,
            entry_zone_low=round(entry * (1 - entry_zone_pct), 8),
            entry_zone_high=round(entry * (1 + entry_zone_pct), 8),
            stop_loss=levels["stop_loss"],
            tp1=levels["tp1"],
            tp2=levels["tp2"],
            tp3=levels["tp3"],
            leverage_suggested=levels.get("leverage", 5),
            risk_percent=2.0,
            confidence_score=round(final_confidence * 100, 1),
            status=SignalStatus.ACTIVE,
            factors=factors,
            ai_reasoning=ai_reasoning_text or f"Multi-TF {direction} setup. R:R {rr}:1. Regime: {levels.get('regime', 'unknown')}. Confidence {final_confidence*100:.0f}%",
            min_tier=min_tier,
            peak_profit_percent=0.0,
            max_drawdown_percent=0.0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        )

        async with async_session() as session:
            session.add(signal)
            await session.commit()
            await session.refresh(signal)
            logger.info(f"Signal #{signal.id} created: {direction.upper()} {symbol} @ {levels['entry']} [exchange={primary_exchange}, ml_p_tp1={ml_prediction.p_tp1:.3f}]")

        # Set Redis cooldown for this coin
        from app.redis_client import set_signal_cooldown
        await set_signal_cooldown(base_symbol, ttl_seconds=self.COIN_COOLDOWN_HOURS * 3600)

        return signal

    def _determine_direction(self, analyses: dict) -> str | None:
        """Multi-timeframe direction consensus."""
        bullish = 0
        bearish = 0

        tf_weights = {"4h": 2.0, "1h": 1.5, "30m": 1.0, "15m": 0.7}

        for tf, data in analyses.items():
            trend = data["trend"]
            weight = tf_weights.get(tf, 1.0)  # Higher TF = more weight, shorter TFs help shorts

            if trend.direction == "bullish":
                bullish += trend.strength * weight
            elif trend.direction == "bearish":
                bearish += trend.strength * weight

            # Pattern direction
            for pattern in data["patterns"]:
                if pattern.direction == "bullish":
                    bullish += pattern.strength * 0.5 * weight
                elif pattern.direction == "bearish":
                    bearish += pattern.strength * 0.5 * weight

        total = bullish + bearish
        if total == 0:
            return None

        if bullish / total > 0.70:
            return "long"
        elif bearish / total > 0.70:
            return "short"
        return None

    def _compute_levels(
        self, indicators: IndicatorSet, direction: str, df: pd.DataFrame,
        regime_result=None,
    ) -> dict | None:
        """Compute entry, SL, TP levels using dynamic ATR multipliers from market regime."""
        from app.signals.regime import detect_regime, get_regime_multipliers

        price = indicators.current_price
        atr = indicators.atr

        if not price or not atr or atr <= 0:
            return None

        # Detect regime if not provided
        if regime_result is None:
            regime_result = detect_regime(indicators)

        sl_m, tp1_m, tp2_m, tp3_m = get_regime_multipliers(regime_result.regime, direction)

        if direction == "long":
            entry = price
            stop_loss = price - atr * sl_m
            tp1 = price + atr * tp1_m
            tp2 = price + atr * tp2_m
            tp3 = price + atr * tp3_m

            # Tighten SL closer to support (but never wider than ATR-based)
            if indicators.support_1 and indicators.support_1 < price:
                candidate_sl = indicators.support_1 - atr * 0.2
                if candidate_sl > stop_loss:  # Only tighten, never widen
                    stop_loss = candidate_sl

        else:  # short
            entry = price
            stop_loss = price + atr * sl_m
            tp1 = price - atr * tp1_m
            tp2 = price - atr * tp2_m
            tp3 = price - atr * tp3_m

            # Tighten SL closer to resistance (but never wider than ATR-based)
            if indicators.resistance_1 and indicators.resistance_1 > price:
                candidate_sl = indicators.resistance_1 + atr * 0.2
                if candidate_sl < stop_loss:  # Only tighten, never widen
                    stop_loss = candidate_sl

        # ── Sanity validation: TP/SL must be in correct direction ──
        if direction == "long":
            if not (stop_loss < entry < tp1 < tp2 < tp3):
                logger.debug(f"Invalid LONG levels: SL={stop_loss}, entry={entry}, TP1={tp1}")
                return None
        else:
            if not (stop_loss > entry > tp1 > tp2 > tp3):
                logger.debug(f"Invalid SHORT levels: SL={stop_loss}, entry={entry}, TP1={tp1}")
                return None

        # Risk/reward validation — must be favorable
        risk = abs(entry - stop_loss)
        reward = abs(tp1 - entry)
        if risk == 0 or reward / risk < 1.5:
            return None

        # Leverage suggestion based on volatility
        atr_pct = (atr / price) * 100
        if atr_pct > 5:
            leverage = 2
        elif atr_pct > 3:
            leverage = 3
        elif atr_pct > 1.5:
            leverage = 5
        else:
            leverage = 10

        return {
            "entry": round(entry, 8),
            "stop_loss": round(stop_loss, 8),
            "tp1": round(tp1, 8),
            "tp2": round(tp2, 8),
            "tp3": round(tp3, 8),
            "leverage": leverage,
            "regime": regime_result.regime.value,
            "regime_strength": round(regime_result.strength, 3),
            "regime_factors": regime_result.factors,
            "multipliers": {"sl": sl_m, "tp1": tp1_m, "tp2": tp2_m, "tp3": tp3_m},
        }


signal_engine = SignalEngine()
