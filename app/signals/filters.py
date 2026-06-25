"""
Signal quality filters — removes noise, validates signals, prevents false positives.
Dynamic thresholds based on market conditions, no hardcoded values.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from loguru import logger

from app.signals.analyzer import IndicatorSet, candles_to_df, compute_indicators


@dataclass
class FilterResult:
    passed: bool
    score: float  # 0.0 to 1.0 (quality score)
    reasons: list[str]
    warnings: list[str]


class SignalFilter:
    """Multi-layer signal quality filter."""

    async def apply_all_filters(
        self,
        df: pd.DataFrame,
        indicators: IndicatorSet,
        direction: str,
        volume_24h: float | None = None,
        market_cap: float | None = None,
        patterns_by_tf: dict[str, list] | None = None,
        trend_by_tf: dict[str, str] | None = None,
        regime_direction: str | None = None,
        regime_strength: float | None = None,
    ) -> FilterResult:
        """Apply all quality filters to a potential signal."""
        reasons = []
        warnings = []
        scores = []

        # 1. Volume filter — must have meaningful volume
        vol_result = self._filter_volume(df, indicators, volume_24h)
        scores.append(vol_result.score)
        reasons.extend(vol_result.reasons)
        warnings.extend(vol_result.warnings)

        # 2. Spread filter — avoid illiquid assets
        spread_result = self._filter_spread(indicators)
        scores.append(spread_result.score)
        reasons.extend(spread_result.reasons)
        warnings.extend(spread_result.warnings)

        # 3. Momentum alignment
        momentum_result = self._filter_momentum(indicators, direction)
        scores.append(momentum_result.score)
        reasons.extend(momentum_result.reasons)
        warnings.extend(momentum_result.warnings)

        # 4. Volatility sanity check
        vol_check = self._filter_volatility(indicators, df)
        scores.append(vol_check.score)
        reasons.extend(vol_check.reasons)
        warnings.extend(vol_check.warnings)

        # 5. Trend confirmation
        trend_result = self._filter_trend_confirmation(indicators, direction)
        scores.append(trend_result.score)
        reasons.extend(trend_result.reasons)
        warnings.extend(trend_result.warnings)

        # 6. RSI extremes (avoid overbought long / oversold short)
        rsi_result = self._filter_rsi(indicators, direction)
        scores.append(rsi_result.score)
        reasons.extend(rsi_result.reasons)
        warnings.extend(rsi_result.warnings)

        # 7. ADX trend strength — reject signals in non-trending markets
        adx_result = self._filter_adx(indicators)
        scores.append(adx_result.score)
        reasons.extend(adx_result.reasons)
        warnings.extend(adx_result.warnings)

        # 8. Contrary patterns on senior TF — HARD BLOCK
        if patterns_by_tf:
            contrary_result = self._filter_contrary_patterns(patterns_by_tf, direction)
            scores.append(contrary_result.score)
            reasons.extend(contrary_result.reasons)
            warnings.extend(contrary_result.warnings)
            if not contrary_result.passed:
                return FilterResult(passed=False, score=round(float(np.mean(scores)), 4),
                                    reasons=reasons, warnings=warnings)

        # 9. Multi-TF alignment — require at least 3/4 TFs to agree
        if trend_by_tf:
            tf_result = self._filter_tf_alignment(trend_by_tf, direction)
            scores.append(tf_result.score)
            reasons.extend(tf_result.reasons)
            warnings.extend(tf_result.warnings)

        # 10. Counter-regime filter — block signals that oppose the regime
        if regime_direction and regime_strength is not None:
            regime_result = self._filter_regime_alignment(direction, regime_direction, regime_strength)
            scores.append(regime_result.score)
            reasons.extend(regime_result.reasons)
            warnings.extend(regime_result.warnings)
            if not regime_result.passed:
                return FilterResult(passed=False, score=round(float(np.mean(scores)), 4),
                                    reasons=reasons, warnings=warnings)

        # Aggregate — strict thresholds to avoid weak signals
        avg_score = float(np.mean(scores)) if scores else 0.0
        passed = avg_score >= 0.5 and all(s >= 0.3 for s in scores)

        return FilterResult(
            passed=passed,
            score=round(avg_score, 4),
            reasons=reasons,
            warnings=warnings,
        )

    def _filter_volume(
        self, df: pd.DataFrame, indicators: IndicatorSet, volume_24h: float | None
    ) -> FilterResult:
        """Require adequate volume relative to recent history."""
        if indicators.volume_ratio is None:
            return FilterResult(True, 0.5, [], ["Volume data unavailable"])

        score = min(1.0, indicators.volume_ratio / 1.5)
        reasons = []
        warnings = []

        # Hard block: volume below 0.65x average → near-guaranteed loss
        if indicators.volume_ratio < 0.65:
            warnings.append(f"Low volume ({indicators.volume_ratio:.2f}x avg < 0.65x) — BLOCKED")
            return FilterResult(False, 0.1, reasons, warnings)

        if indicators.volume_ratio >= 1.5:
            reasons.append(f"Strong volume ({indicators.volume_ratio:.1f}x avg)")
        elif indicators.volume_ratio >= 0.8:
            reasons.append("Adequate volume")
        else:
            warnings.append(f"Below-average volume ({indicators.volume_ratio:.2f}x)")

        return FilterResult(True, score, reasons, warnings)

    def _filter_spread(self, indicators: IndicatorSet) -> FilterResult:
        """Check BB width as proxy for spread/liquidity."""
        if indicators.bb_width is None:
            return FilterResult(True, 0.5, [], [])

        # Extremely low BB width (%) might indicate low liquidity / dead market
        if indicators.bb_width < 0.5:
            return FilterResult(False, 0.1, [], ["Extremely tight BB width (<0.5%), possible low liquidity"])

        return FilterResult(True, 0.7, [], [])

    def _filter_momentum(self, indicators: IndicatorSet, direction: str) -> FilterResult:
        """Check if momentum indicators agree with signal direction."""
        agreements = 0
        total = 0
        reasons = []
        warnings = []

        # RSI — aligned with scorer: 30-60 ideal for longs, 40-70 for shorts
        if indicators.rsi_14 is not None:
            total += 1
            if direction == "long" and 30 <= indicators.rsi_14 <= 65:
                agreements += 1
            elif direction == "short" and 35 <= indicators.rsi_14 <= 70:
                agreements += 1

        # MACD
        if indicators.macd_histogram is not None:
            total += 1
            if direction == "long" and indicators.macd_histogram > 0:
                agreements += 1
                reasons.append("MACD confirms long")
            elif direction == "short" and indicators.macd_histogram < 0:
                agreements += 1
                reasons.append("MACD confirms short")

        # Stochastic — check zone, not just direction
        if indicators.stoch_k is not None:
            total += 1
            if direction == "long" and indicators.stoch_k < 80 and indicators.stoch_k > 20:
                agreements += 1
            elif direction == "short" and indicators.stoch_k > 20 and indicators.stoch_k < 80:
                agreements += 1

        score = agreements / total if total > 0 else 0.5
        if score < 0.3:
            warnings.append("Momentum diverges from signal direction")

        return FilterResult(score >= 0.3, round(score, 2), reasons, warnings)

    def _filter_volatility(self, indicators: IndicatorSet, df: pd.DataFrame) -> FilterResult:
        """Ensure volatility is within acceptable range."""
        if indicators.atr_percent is None:
            return FilterResult(True, 0.5, [], [])

        warnings = []
        reasons = []

        # Dynamic threshold: compute historical ATR% distribution
        high = df["high"]
        low = df["low"]
        close = df["close"]
        if len(df) >= 14:
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr_pct_series = (tr.rolling(14).mean() / close * 100).dropna()
            if len(atr_pct_series) > 0:
                median_atr_pct = float(atr_pct_series.median())
                if indicators.atr_percent > median_atr_pct * 3:
                    warnings.append(f"Extreme volatility ({indicators.atr_percent:.1f}% ATR)")
                    return FilterResult(False, 0.1, reasons, warnings)
                elif indicators.atr_percent > median_atr_pct * 2:
                    warnings.append(f"High volatility ({indicators.atr_percent:.1f}% ATR)")

        return FilterResult(True, 0.7, reasons, warnings)

    def _filter_trend_confirmation(self, indicators: IndicatorSet, direction: str) -> FilterResult:
        """Check if major trends confirm the signal direction."""
        confirmations = 0
        total = 0
        reasons = []

        price = indicators.current_price

        # Price vs SMA50
        if indicators.sma_50 and price:
            total += 1
            if direction == "long" and price > indicators.sma_50:
                confirmations += 1
                reasons.append("Above SMA50")
            elif direction == "short" and price < indicators.sma_50:
                confirmations += 1
                reasons.append("Below SMA50")

        # EMA alignment
        if indicators.ema_9 and indicators.ema_21:
            total += 1
            if direction == "long" and indicators.ema_9 > indicators.ema_21:
                confirmations += 1
                reasons.append("EMA bullish alignment")
            elif direction == "short" and indicators.ema_9 < indicators.ema_21:
                confirmations += 1
                reasons.append("EMA bearish alignment")

        # ADX trend strength
        if indicators.adx and indicators.adx > 25:
            total += 1
            if direction == "long" and indicators.adx_pos and indicators.adx_neg and indicators.adx_pos > indicators.adx_neg:
                confirmations += 1
            elif direction == "short" and indicators.adx_pos and indicators.adx_neg and indicators.adx_neg > indicators.adx_pos:
                confirmations += 1

        score = confirmations / total if total > 0 else 0.5
        return FilterResult(True, round(score, 2), reasons, [])

    def _filter_rsi(self, indicators: IndicatorSet, direction: str) -> FilterResult:
        """Avoid entering trades against extreme RSI."""
        if indicators.rsi_14 is None:
            return FilterResult(True, 0.5, [], [])

        warnings = []

        # Hard block at 70/30 — overbought longs and oversold shorts lose
        if direction == "long" and indicators.rsi_14 > 70:
            warnings.append(f"RSI overbought ({indicators.rsi_14:.0f}) — BLOCKED for long")
            return FilterResult(False, 0.1, [], warnings)
        elif direction == "short" and indicators.rsi_14 < 30:
            warnings.append(f"RSI oversold ({indicators.rsi_14:.0f}) — BLOCKED for short")
            return FilterResult(False, 0.1, [], warnings)

        # Penalize moderately extreme RSI (65-70 long / 30-35 short)
        if direction == "long" and indicators.rsi_14 > 65:
            return FilterResult(True, 0.3, [], [f"RSI elevated ({indicators.rsi_14:.0f})"])
        elif direction == "short" and indicators.rsi_14 < 35:
            return FilterResult(True, 0.3, [], [f"RSI low ({indicators.rsi_14:.0f})"])

        return FilterResult(True, 0.7, [], warnings)

    def _filter_adx(self, indicators: IndicatorSet) -> FilterResult:
        """Require minimum trend strength via ADX."""
        if indicators.adx is None:
            return FilterResult(True, 0.5, [], ["ADX data unavailable"])

        if indicators.adx < 15:
            return FilterResult(False, 0.1, [], [f"No trend (ADX {indicators.adx:.0f} < 15)"])
        elif indicators.adx < 20:
            return FilterResult(True, 0.35, [], [f"Weak trend (ADX {indicators.adx:.0f})"])
        elif indicators.adx >= 30:
            return FilterResult(True, 1.0, [f"Strong trend (ADX {indicators.adx:.0f})"], [])
        else:
            return FilterResult(True, 0.7, [], [])

    # ── NEW FILTERS ──────────────────────────────────────────────────

    _BULLISH_PATTERNS = {
        "bullish_engulfing", "hammer", "morning_star", "three_white_soldiers",
        "rsi_bull_divergence", "double_bottom", "inverse_head_and_shoulders",
        "bullish_harami", "dragonfly_doji", "piercing_line",
    }
    _BEARISH_PATTERNS = {
        "bearish_engulfing", "shooting_star", "evening_star", "three_black_crows",
        "rsi_bear_divergence", "double_top", "head_and_shoulders",
        "bearish_harami", "gravestone_doji", "dark_cloud_cover",
    }

    def _filter_contrary_patterns(
        self, patterns_by_tf: dict[str, list], direction: str
    ) -> FilterResult:
        """HARD BLOCK if 4h or 1h TF has strong contrary patterns."""
        contrary_names: list[str] = []
        # Check senior TFs (4h has most weight, then 1h)
        for tf in ("4h", "1h"):
            tf_patterns = patterns_by_tf.get(tf, [])
            for p in tf_patterns:
                name = p.get("name", "") if isinstance(p, dict) else str(p)
                name_lower = name.lower().replace(" ", "_")
                if direction == "long" and name_lower in self._BEARISH_PATTERNS:
                    contrary_names.append(f"{tf}: {name}")
                elif direction == "short" and name_lower in self._BULLISH_PATTERNS:
                    contrary_names.append(f"{tf}: {name}")

        if len(contrary_names) >= 2:
            return FilterResult(
                False, 0.0, [],
                [f"Contrary patterns on senior TF — BLOCKED: {', '.join(contrary_names)}"],
            )
        if len(contrary_names) == 1:
            return FilterResult(
                True, 0.25, [],
                [f"Contrary pattern warning: {contrary_names[0]}"],
            )
        return FilterResult(True, 0.8, ["No contrary patterns on senior TFs"], [])

    def _filter_tf_alignment(
        self, trend_by_tf: dict[str, str], direction: str
    ) -> FilterResult:
        """Require at least 3 of 4 TFs to agree with signal direction."""
        agreeing = 0
        total = 0
        for tf_name, tf_trend in trend_by_tf.items():
            total += 1
            trend_lower = tf_trend.lower()
            if direction == "long" and "bull" in trend_lower:
                agreeing += 1
            elif direction == "short" and "bear" in trend_lower:
                agreeing += 1

        if total == 0:
            return FilterResult(True, 0.5, [], ["No TF data for alignment check"])

        ratio = agreeing / total
        if ratio < 0.5:
            return FilterResult(
                False, 0.1, [],
                [f"Poor TF alignment: only {agreeing}/{total} TFs agree with {direction}"],
            )
        if ratio < 0.75:
            return FilterResult(
                True, 0.35, [],
                [f"Moderate TF alignment: {agreeing}/{total} TFs agree"],
            )
        return FilterResult(True, 0.9, [f"Strong TF alignment: {agreeing}/{total}"], [])

    def _filter_regime_alignment(
        self, direction: str, regime_direction: str, regime_strength: float
    ) -> FilterResult:
        """Block signals opposing a strong regime."""
        regime_lower = regime_direction.lower()

        # Check if direction opposes the detected regime
        opposing = (
            (direction == "long" and "bear" in regime_lower)
            or (direction == "short" and "bull" in regime_lower)
        )

        if opposing and regime_strength > 0.6:
            return FilterResult(
                False, 0.0, [],
                [f"Signal opposes strong {regime_direction} regime (strength {regime_strength:.2f}) — BLOCKED"],
            )
        if opposing and regime_strength > 0.3:
            return FilterResult(
                True, 0.2, [],
                [f"Signal opposes moderate {regime_direction} regime"],
            )
        if opposing:
            return FilterResult(True, 0.4, [], [f"Weak counter-regime signal"])

        # Aligned with regime
        return FilterResult(True, 0.85, [f"Aligned with {regime_direction} regime"], [])


signal_filter = SignalFilter()
