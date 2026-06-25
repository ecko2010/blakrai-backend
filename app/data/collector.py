"""
Historical data collector — fetches and stores OHLCV candles + coin metadata
from all exchanges and CoinGecko.

Designed to run as scheduler tasks without breaking existing functionality.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, and_, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models import CandleRecord, CandleTimeframe, CoinMeta, MarketSnapshot
from app.exchanges.manager import exchange_manager
from app.data.coingecko import coingecko


# ─── Configuration ──────────────────────────────────────

# Which timeframes to collect and how often
TIMEFRAME_CONFIG = {
    CandleTimeframe.M15: {"interval": "15m", "limit": 96, "collect_every_min": 15, "keep_days": 7},
    CandleTimeframe.H1:  {"interval": "1h",  "limit": 200, "collect_every_min": 60, "keep_days": 30},
    CandleTimeframe.H4:  {"interval": "4h",  "limit": 200, "collect_every_min": 240, "keep_days": 90},
    CandleTimeframe.D1:  {"interval": "1d",  "limit": 365, "collect_every_min": 1440, "keep_days": 365},
}

# Expanded coin pool — 300 coins (up from 100)
MAX_COINS_TO_TRACK = 300

# Max concurrent requests PER exchange (rate limit safety)
EXCHANGE_CONCURRENCY = 2

# Delay between exchange batches (seconds)
INTER_EXCHANGE_DELAY = 1.0

# Delay between coin requests within an exchange (seconds)
INTER_COIN_DELAY = 0.15


# ─── Candle Collector ───────────────────────────────────

async def collect_candles(timeframe: CandleTimeframe):
    """Fetch OHLCV candles for the given timeframe from all exchanges.

    Uses upsert (ON CONFLICT DO NOTHING) to avoid duplicates.
    Rate-limited to avoid exchange API bans.
    """
    config = TIMEFRAME_CONFIG[timeframe]
    interval = config["interval"]
    limit = config["limit"]

    # Get top coins by recent snapshot volume
    top_coins = await _get_top_tracked_coins()
    if not top_coins:
        logger.warning("No coins to collect candles for")
        return 0

    total_saved = 0
    total_errors = 0

    for name, exchange in exchange_manager.exchanges.items():
        sem = asyncio.Semaphore(EXCHANGE_CONCURRENCY)
        exchange_saved = 0

        async def _fetch_coin(symbol: str):
            nonlocal exchange_saved, total_errors
            async with sem:
                try:
                    klines = await exchange.get_klines(symbol, interval, limit)
                    if not klines:
                        return

                    rows = []
                    for k in klines:
                        rows.append({
                            "coin_symbol": symbol,
                            "exchange": name,
                            "timeframe": timeframe,
                            "open_time": k.timestamp,
                            "open": k.open,
                            "high": k.high,
                            "low": k.low,
                            "close": k.close,
                            "volume": k.volume,
                        })

                    if rows:
                        async with async_session() as session:
                            stmt = pg_insert(CandleRecord).values(rows)
                            stmt = stmt.on_conflict_do_nothing(constraint="uq_candle")
                            result = await session.execute(stmt)
                            await session.commit()
                            exchange_saved += result.rowcount or 0

                    # Rate limit between coins
                    await asyncio.sleep(INTER_COIN_DELAY)

                except Exception as e:
                    total_errors += 1
                    logger.debug(f"Candle fetch {name}/{symbol}/{interval}: {e}")

        # Process coins in batches of 20 per exchange
        batch_size = 20
        for i in range(0, len(top_coins), batch_size):
            batch = top_coins[i:i + batch_size]
            await asyncio.gather(*[_fetch_coin(s) for s in batch])
            if i + batch_size < len(top_coins):
                await asyncio.sleep(0.5)  # Pause between batches

        total_saved += exchange_saved
        # Delay between exchanges to spread load
        await asyncio.sleep(INTER_EXCHANGE_DELAY)

    logger.info(f"Candles [{interval}]: {total_saved} new rows, {total_errors} errors across {len(exchange_manager.exchanges)} exchanges")
    return total_saved


async def backfill_candles():
    """One-time backfill of historical candles for all timeframes.

    Safe to run multiple times — upsert prevents duplicates.
    """
    logger.info("Starting candle backfill...")
    total = 0
    for tf in [CandleTimeframe.D1, CandleTimeframe.H4, CandleTimeframe.H1]:
        count = await collect_candles(tf)
        total += (count or 0)
        await asyncio.sleep(2)  # Rate limit courtesy
    logger.info(f"Backfill complete: {total} total candles stored")
    return total


# ─── Coin Metadata Collector ────────────────────────────

async def collect_coin_metadata():
    """Refresh coin metadata from CoinGecko (logos, market cap, supply, etc.).

    Runs daily — enriches our symbols with CoinGecko data.
    Uses /coins/markets for accurate symbol→ID mapping (avoids ambiguity
    from /coins/list where multiple coins share the same symbol).
    Pre-fetches exchange symbols once to avoid N+1 queries.
    """
    try:
        # Step 1: Get all symbols we track from recent snapshots
        tracked_symbols = await _get_top_tracked_coins()
        if not tracked_symbols:
            return

        # Step 2: Fetch market data from CoinGecko (sorted by market cap)
        # This gives us accurate symbol→ID mapping because top coins
        # by market cap are the ones exchanges actually list.
        market_data = await coingecko.get_market_data(
            per_page=250, page=1, sparkline=False,
            price_change_pct="1h,24h,7d,30d",
        )
        await asyncio.sleep(1.5)  # CoinGecko rate limit

        if len(tracked_symbols) > 150:
            page2 = await coingecko.get_market_data(
                per_page=250, page=2, sparkline=False,
                price_change_pct="1h,24h,7d,30d",
            )
            market_data.extend(page2)

        # Build symbol→CoinGecko data mapping from market data directly.
        # Use highest-market-cap match when multiple coins share a symbol.
        symbol_to_cg_data: dict[str, dict] = {}
        for item in market_data:
            sym = item.get("symbol", "").upper()
            base_sym = f"{sym}USDT"
            if base_sym in tracked_symbols and base_sym not in symbol_to_cg_data:
                # First match wins — market data is already sorted by market cap
                symbol_to_cg_data[base_sym] = item

        # Step 3: Pre-fetch all exchange symbols ONCE (fixes N+1 problem)
        exchange_symbols: dict[str, set[str]] = {}
        for ename, ex in exchange_manager.exchanges.items():
            try:
                symbols = await ex.get_symbols()
                exchange_symbols[ename] = set(symbols) if isinstance(symbols, list) else symbols
            except Exception:
                exchange_symbols[ename] = set()
            await asyncio.sleep(0.3)

        # Step 4: Upsert coin metadata (batch — pre-fetch all existing)
        updated = 0
        async with async_session() as session:
            # Pre-fetch all existing CoinMeta in one query
            result = await session.execute(
                select(CoinMeta).where(CoinMeta.symbol.in_(tracked_symbols))
            )
            existing_meta = {m.symbol: m for m in result.scalars().all()}

            for symbol in tracked_symbols:
                cg_data = symbol_to_cg_data.get(symbol, {})

                meta = existing_meta.get(symbol)
                if meta is None:
                    meta = CoinMeta(symbol=symbol)
                    session.add(meta)

                if cg_data:
                    meta.coingecko_id = cg_data.get("id", meta.coingecko_id)
                    meta.name = cg_data.get("name", meta.name)
                    meta.logo_url = cg_data.get("image", meta.logo_url)
                    meta.logo_thumb_url = cg_data.get("image", meta.logo_thumb_url)
                    meta.market_cap = cg_data.get("market_cap", meta.market_cap)
                    meta.market_cap_rank = cg_data.get("market_cap_rank", meta.market_cap_rank)
                    meta.total_supply = cg_data.get("total_supply", meta.total_supply)
                    meta.circulating_supply = cg_data.get("circulating_supply", meta.circulating_supply)
                    meta.max_supply = cg_data.get("max_supply", meta.max_supply)
                    meta.ath = cg_data.get("ath", meta.ath)
                    meta.atl = cg_data.get("atl", meta.atl)
                    if cg_data.get("ath_date"):
                        try:
                            meta.ath_date = datetime.fromisoformat(cg_data["ath_date"].replace("Z", "+00:00"))
                        except Exception:
                            pass
                    if cg_data.get("atl_date"):
                        try:
                            meta.atl_date = datetime.fromisoformat(cg_data["atl_date"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                # Use pre-fetched exchange symbols (O(1) lookup per exchange)
                exchanges_with_coin = []
                for ename, syms in exchange_symbols.items():
                    if symbol in syms or symbol.replace("USDT", "/USDT") in syms:
                        exchanges_with_coin.append(ename)
                if exchanges_with_coin:
                    meta.exchanges_available = exchanges_with_coin

                updated += 1

            await session.commit()

        matched = len(symbol_to_cg_data)
        logger.info(f"Coin metadata updated: {updated} coins ({matched} matched to CoinGecko)")
        return updated

    except Exception as e:
        logger.error(f"Coin metadata collection failed: {e}", exc_info=True)
        return 0


# ─── AI Daily Analysis ──────────────────────────────────

async def run_daily_ai_analysis():
    """Generate AI analysis for top coins and overall market.

    Creates three types of analysis entries:
    - market_overview: global market state
    - coin_analysis: per-coin analysis for top 20
    - trend_report: cross-coin patterns and correlations
    """
    from app.models import DailyAIAnalysis, Signal

    today = datetime.now(timezone.utc).date()

    # Check if already ran today
    async with async_session() as session:
        existing = await session.scalar(
            select(func.count(DailyAIAnalysis.id)).where(
                DailyAIAnalysis.date == today,
                DailyAIAnalysis.analysis_type == "market_overview",
            )
        )
        if existing:
            logger.info("Daily AI analysis already completed for today")
            return

    try:
        # Gather context
        global_data = await coingecko.get_global_data()
        fear_greed = await coingecko.get_fear_greed_index()
        trending = await coingecko.get_trending()

        # Get recent signal performance
        async with async_session() as session:
            cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
            recent_signals = await session.execute(
                select(Signal).where(Signal.created_at >= cutoff_7d).order_by(Signal.created_at.desc()).limit(50)
            )
            signals = recent_signals.scalars().all()

            # Get 24h candle data for top coins
            cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            top_candles = await session.execute(
                select(CandleRecord).where(
                    CandleRecord.timeframe == CandleTimeframe.H1,
                    CandleRecord.open_time >= cutoff_24h,
                ).order_by(CandleRecord.open_time)
            )
            candles_24h = top_candles.scalars().all()

        # Build market context
        total_mcap = global_data.get("total_market_cap", {}).get("usd", 0)
        btc_dom = global_data.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = global_data.get("market_cap_percentage", {}).get("eth", 0)
        mcap_change = global_data.get("market_cap_change_percentage_24h_usd", 0)

        fg_text = ""
        if fear_greed:
            fg_text = f"Fear & Greed Index: {fear_greed['value']}/100 ({fear_greed['classification']}). "

        trending_coins = []
        try:
            for item in trending.get("coins", [])[:7]:
                coin = item.get("item", {})
                trending_coins.append(coin.get("symbol", "?"))
        except Exception:
            pass

        # Signal performance summary
        win_count = sum(1 for s in signals if s.pnl_percent and s.pnl_percent > 0)
        loss_count = sum(1 for s in signals if s.pnl_percent and s.pnl_percent <= 0)
        active_count = sum(1 for s in signals if s.status.value == "active")
        avg_pnl = 0
        if signals:
            pnls = [s.pnl_percent for s in signals if s.pnl_percent is not None]
            avg_pnl = sum(pnls) / len(pnls) if pnls else 0

        # Group candles by coin for mini-analysis
        coin_candles = {}
        for c in candles_24h:
            coin_candles.setdefault(c.coin_symbol, []).append(c)

        # ── 1. Market Overview ──
        market_overview = (
            f"📊 Daily Market Overview — {today.isoformat()}\n\n"
            f"Total Market Cap: ${total_mcap / 1e9:,.1f}B ({mcap_change:+.1f}% 24h)\n"
            f"BTC Dominance: {btc_dom:.1f}% | ETH Dominance: {eth_dom:.1f}%\n"
            f"{fg_text}\n"
            f"Trending: {', '.join(trending_coins) if trending_coins else 'N/A'}\n\n"
            f"🤖 Signal Performance (7d):\n"
            f"• Active: {active_count} signals\n"
            f"• Win/Loss: {win_count}/{loss_count}\n"
            f"• Avg PnL: {avg_pnl:+.2f}%\n"
        )

        market_metrics = {
            "total_market_cap_usd": total_mcap,
            "btc_dominance": btc_dom,
            "eth_dominance": eth_dom,
            "mcap_change_24h": mcap_change,
            "fear_greed": fear_greed,
            "signals_active": active_count,
            "signals_win_7d": win_count,
            "signals_loss_7d": loss_count,
            "avg_pnl_7d": avg_pnl,
        }

        # ── 2. Top Coin Analysis ──
        coin_analyses = []
        top_coins_for_analysis = sorted(
            coin_candles.keys(),
            key=lambda sym: len(coin_candles[sym]),
            reverse=True
        )[:20]

        for symbol in top_coins_for_analysis:
            candles = sorted(coin_candles[symbol], key=lambda c: c.open_time)
            if len(candles) < 4:
                continue

            opens = [c.open for c in candles]
            closes = [c.close for c in candles]
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]
            volumes = [c.volume for c in candles]

            price_start = opens[0]
            price_end = closes[-1]
            change_pct = ((price_end - price_start) / price_start * 100) if price_start else 0
            high_24h = max(highs)
            low_24h = min(lows)
            volatility = ((high_24h - low_24h) / low_24h * 100) if low_24h else 0
            avg_vol = sum(volumes) / len(volumes) if volumes else 0
            vol_trend = volumes[-1] / avg_vol if avg_vol else 1

            # Simple trend detection
            if change_pct > 3:
                trend = "🟢 Bullish"
            elif change_pct < -3:
                trend = "🔴 Bearish"
            else:
                trend = "🟡 Sideways"

            analysis = (
                f"{symbol}: {trend} ({change_pct:+.2f}%)\n"
                f"  Price: ${price_end:,.4f} | Range: ${low_24h:,.4f}-${high_24h:,.4f}\n"
                f"  Volatility: {volatility:.1f}% | Volume trend: {vol_trend:.1f}x avg\n"
            )

            # Check for related signals
            symbol_signals = [s for s in signals if s.coin_symbol == symbol]
            if symbol_signals:
                recent = symbol_signals[0]
                analysis += f"  📡 Recent signal: {recent.direction.value.upper()} (conf: {recent.confidence_score:.0%})\n"

            coin_analyses.append({
                "symbol": symbol,
                "analysis": analysis,
                "metrics": {
                    "price": price_end,
                    "change_24h": change_pct,
                    "volatility": volatility,
                    "volume_trend": vol_trend,
                    "trend": trend,
                }
            })

        coin_analysis_text = "📈 Top Coin Analysis — 24h\n\n" + "\n".join(
            a["analysis"] for a in coin_analyses
        )

        # ── 3. Trend Report ──
        bullish_coins = [a for a in coin_analyses if "Bullish" in a["metrics"]["trend"]]
        bearish_coins = [a for a in coin_analyses if "Bearish" in a["metrics"]["trend"]]

        trend_report = (
            f"📋 Trend Report — {today.isoformat()}\n\n"
            f"Bullish ({len(bullish_coins)}): {', '.join(a['symbol'] for a in bullish_coins[:10])}\n"
            f"Bearish ({len(bearish_coins)}): {', '.join(a['symbol'] for a in bearish_coins[:10])}\n\n"
        )

        # High volatility alert
        high_vol = sorted(coin_analyses, key=lambda a: a["metrics"]["volatility"], reverse=True)[:5]
        if high_vol:
            trend_report += "⚡ Highest Volatility:\n"
            for a in high_vol:
                trend_report += f"  {a['symbol']}: {a['metrics']['volatility']:.1f}%\n"

        # Volume spike detection
        vol_spikes = [a for a in coin_analyses if a["metrics"]["volume_trend"] > 2.0]
        if vol_spikes:
            trend_report += f"\n📊 Volume Spikes (>2x avg):\n"
            for a in vol_spikes:
                trend_report += f"  {a['symbol']}: {a['metrics']['volume_trend']:.1f}x\n"

        # Save all analyses
        async with async_session() as session:
            session.add(DailyAIAnalysis(
                date=today,
                coin_symbol=None,
                analysis_type="market_overview",
                content=market_overview,
                metrics=market_metrics,
            ))
            session.add(DailyAIAnalysis(
                date=today,
                coin_symbol=None,
                analysis_type="trend_report",
                content=trend_report,
                metrics={
                    "bullish_count": len(bullish_coins),
                    "bearish_count": len(bearish_coins),
                    "high_volatility": [a["symbol"] for a in high_vol],
                    "volume_spikes": [a["symbol"] for a in vol_spikes],
                },
            ))

            for ca in coin_analyses:
                session.add(DailyAIAnalysis(
                    date=today,
                    coin_symbol=ca["symbol"],
                    analysis_type="coin_analysis",
                    content=ca["analysis"],
                    metrics=ca["metrics"],
                ))

            await session.commit()

        logger.info(f"Daily AI analysis complete: overview + {len(coin_analyses)} coin analyses + trend report")

    except Exception as e:
        logger.error(f"Daily AI analysis failed: {e}", exc_info=True)


# ─── Cleanup ────────────────────────────────────────────

async def cleanup_old_candles():
    """Remove old candle data based on retention policy per timeframe."""
    try:
        total_deleted = 0
        async with async_session() as session:
            for tf, config in TIMEFRAME_CONFIG.items():
                cutoff = datetime.now(timezone.utc) - timedelta(days=config["keep_days"])
                result = await session.execute(
                    text(
                        "DELETE FROM candles WHERE timeframe = :tf AND open_time < :cutoff"
                    ),
                    {"tf": tf.value, "cutoff": cutoff},
                )
                deleted = result.rowcount or 0
                total_deleted += deleted
                if deleted:
                    logger.info(f"Cleaned {deleted} old candles [{tf.value}] (>{config['keep_days']}d)")

            # Also clean old daily AI analyses (keep 90 days)
            cutoff_ai = datetime.now(timezone.utc).date() - timedelta(days=90)
            result = await session.execute(
                text("DELETE FROM daily_ai_analysis WHERE date < :cutoff"),
                {"cutoff": cutoff_ai},
            )
            ai_deleted = result.rowcount or 0
            if ai_deleted:
                logger.info(f"Cleaned {ai_deleted} old AI analyses (>90d)")

            # Clean old MarketSnapshots (keep 30 days — ~2400 rows/hr unbounded otherwise)
            cutoff_snap = datetime.now(timezone.utc) - timedelta(days=30)
            result = await session.execute(
                text("DELETE FROM market_snapshots WHERE created_at < :cutoff"),
                {"cutoff": cutoff_snap},
            )
            snap_deleted = result.rowcount or 0
            if snap_deleted:
                logger.info(f"Cleaned {snap_deleted} old market snapshots (>30d)")

            await session.commit()

        logger.info(f"Cleanup complete: {total_deleted} candle rows + {ai_deleted} AI rows + {snap_deleted} snapshot rows removed")
    except Exception as e:
        logger.error(f"Candle cleanup failed: {e}", exc_info=True)


# ─── Helpers ────────────────────────────────────────────

async def _get_top_tracked_coins() -> list[str]:
    """Get the most active coin symbols based on recent snapshots and signals."""
    try:
        async with async_session() as session:
            # Get distinct coins from recent snapshots, ordered by frequency
            result = await session.execute(
                select(MarketSnapshot.coin_symbol)
                .group_by(MarketSnapshot.coin_symbol)
                .order_by(func.count(MarketSnapshot.id).desc())
                .limit(MAX_COINS_TO_TRACK)
            )
            coins = [row[0] for row in result.all()]
            if coins:
                return coins

            # Fallback: get from exchanges directly
            all_symbols = set()
            try:
                binance = exchange_manager.get_exchange("binance")
                tickers = await binance.get_all_tickers()
                all_symbols = {t.symbol for t in tickers[:MAX_COINS_TO_TRACK]}
            except Exception:
                pass

            return list(all_symbols)[:MAX_COINS_TO_TRACK]
    except Exception as e:
        logger.error(f"Failed to get tracked coins: {e}")
        return []
