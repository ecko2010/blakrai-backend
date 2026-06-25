"""
Market regime detection — determines whether the market is trending, ranging,
or in high volatility mode. Used by the signal engine to adapt R:R levels.
"""

from enum import Enum
from dataclasses import dataclass
from loguru import logger

from app.signals.analyzer import IndicatorSet


class MarketRegime(str, Enum):
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"


@dataclass
class RegimeResult:
    regime: MarketRegime
    strength: float  # 0.0 to 1.0 — how confident we are in this regime
    factors: list[str]  # human-readable reasons


def detect_regime(indicators: IndicatorSet) -> RegimeResult:
    """Detect market regime from technical indicators.

    Logic:
      1. ATR% > 6% → HIGH_VOLATILITY (extreme moves dominate)
      2. ADX > 25 → TRENDING, direction from SMA50/SMA200 + EMA structure
      3. ADX ≤ 25 + BB squeeze (width < 4%) → RANGING
      4. Fallback → RANGING
    """
    factors: list[str] = []
    adx = indicators.adx
    atr_pct = indicators.atr_percent  # ATR / price * 100
    sma50 = indicators.sma_50
    sma200 = indicators.sma_200
    bb_width = indicators.bb_width  # (upper - lower) / middle * 100
    ema_9 = indicators.ema_9
    ema_21 = indicators.ema_21
    ema_55 = indicators.ema_55
    rsi = indicators.rsi_14
    price = indicators.current_price

    # ── Step 1: High volatility override ──
    if atr_pct is not None and atr_pct > 6.0:
        strength = min(1.0, atr_pct / 10.0)
        factors.append(f"ATR%={atr_pct:.1f}% (extreme volatility)")
        if bb_width is not None and bb_width > 10.0:
            factors.append(f"BB width={bb_width:.1f}% (wide)")
        return RegimeResult(
            regime=MarketRegime.HIGH_VOLATILITY,
            strength=strength,
            factors=factors,
        )

    # ── Step 2: Trending check (ADX > 25) ──
    if adx is not None and adx > 25:
        # Determine direction — SMA50/200 is the PRIMARY macro signal (weight 3x)
        # EMA 9/21/55 is secondary (weight 1x) because it can flip fast in corrections
        bull_signals = 0
        bear_signals = 0

        has_death_cross = False
        has_golden_cross = False

        # SMA 50/200 golden/death cross — DOMINANT factor (weight=3)
        if sma50 is not None and sma200 is not None:
            if sma50 > sma200:
                bull_signals += 3
                has_golden_cross = True
                factors.append("SMA50 > SMA200 (golden cross)")
            else:
                bear_signals += 3
                has_death_cross = True
                factors.append("SMA50 < SMA200 (death cross)")

        # EMA structure: 9 > 21 > 55 — secondary (weight=1)
        # If it contradicts SMA cross, it's a short-term counter-move, NOT a regime change
        if ema_9 is not None and ema_21 is not None and ema_55 is not None:
            if ema_9 > ema_21 > ema_55:
                if has_death_cross:
                    # EMA bull alignment during death cross = dead cat bounce, penalize
                    bull_signals += 1
                    factors.append("EMA 9>21>55 (bull alignment — counter to death cross)")
                else:
                    bull_signals += 2
                    factors.append("EMA 9>21>55 (bull alignment)")
            elif ema_9 < ema_21 < ema_55:
                if has_golden_cross:
                    bear_signals += 1
                    factors.append("EMA 9<21<55 (bear alignment — counter to golden cross)")
                else:
                    bear_signals += 2
                    factors.append("EMA 9<21<55 (bear alignment)")

        # Price vs SMA200 — weight=2 (stronger than EMA)
        if price is not None and sma200 is not None and sma200 > 0:
            pct_above = (price - sma200) / sma200 * 100
            if pct_above > 5:
                bull_signals += 2
                factors.append(f"Price {pct_above:.1f}% above SMA200")
            elif pct_above < -5:
                bear_signals += 2
                factors.append(f"Price {pct_above:.1f}% below SMA200")

        # RSI bias (weight=1)
        if rsi is not None:
            if rsi > 55:
                bull_signals += 1
            elif rsi < 45:
                bear_signals += 1

        factors.append(f"ADX={adx:.1f} (trending)")

        # Trend strength: ADX capped at ~50 for max strength
        trend_strength = min(1.0, (adx - 25) / 25)

        # If conflicting signals (death cross but EMA bull), reduce strength significantly
        if has_death_cross and bull_signals > bear_signals:
            trend_strength *= 0.3  # Very weak trending_bull claim
        elif has_golden_cross and bear_signals > bull_signals:
            trend_strength *= 0.3

        if bull_signals > bear_signals:
            return RegimeResult(
                regime=MarketRegime.TRENDING_BULL,
                strength=trend_strength,
                factors=factors,
            )
        elif bear_signals > bull_signals:
            return RegimeResult(
                regime=MarketRegime.TRENDING_BEAR,
                strength=trend_strength,
                factors=factors,
            )
        else:
            # Tied — use SMA200 as tiebreaker (macro wins)
            if price is not None and sma200 is not None and price > sma200:
                return RegimeResult(
                    regime=MarketRegime.TRENDING_BULL,
                    strength=trend_strength * 0.4,
                    factors=factors + ["direction tie → price above SMA200"],
                )
            else:
                return RegimeResult(
                    regime=MarketRegime.TRENDING_BEAR,
                    strength=trend_strength * 0.4,
                    factors=factors + ["direction tie → price below SMA200"],
                )

    # ── Step 3: Low ADX — ranging or low-vol ──
    factors.append(f"ADX={adx:.1f} (low trend strength)" if adx else "ADX=N/A")

    if bb_width is not None and bb_width < 4.0:
        factors.append(f"BB width={bb_width:.1f}% (squeeze → ranging)")

    # Moderate volatility without trend = ranging
    strength = 0.6
    if adx is not None:
        strength = min(1.0, (25 - adx) / 15)  # Lower ADX = more confident it's ranging

    return RegimeResult(
        regime=MarketRegime.RANGING,
        strength=strength,
        factors=factors,
    )


# ── Dynamic ATR multipliers per regime ──

# Columns: (sl_mult, tp1_mult, tp2_mult, tp3_mult)
# "aligned" = signal direction matches trend (long in bull, short in bear)
# "counter" = signal direction opposes trend

_REGIME_MULTIPLIERS = {
    # Trend-aligned trades: tight SL, wide TPs (ride the trend)
    # R:R = 2.5/1.2 = 2.08:1 ✓
    "trend_aligned": (1.2, 2.5, 4.5, 7.0),
    # Counter-trend trades: tight SL (quick invalidation), moderate TPs
    # R:R = 2.0/1.2 = 1.67:1 ✓  (was 1.5/1.8 = 0.83:1 ✗)
    "trend_counter": (1.2, 2.0, 3.0, 4.5),
    # Ranging: mean-reversion — tight SL near S/R boundary, moderate TPs to opposite boundary
    # R:R = 2.0/1.0 = 2.0:1 ✓  (was 1.5/1.8 = 0.83:1 ✗)
    "ranging": (1.0, 2.0, 3.0, 4.0),
    # High volatility: moderate SL, wide TPs (big moves expected)
    # R:R = 3.0/1.8 = 1.67:1 ✓
    "high_volatility": (1.8, 3.0, 5.0, 8.0),
}


def get_regime_multipliers(
    regime: MarketRegime, direction: str
) -> tuple[float, float, float, float]:
    """Return (sl_mult, tp1_mult, tp2_mult, tp3_mult) based on regime + direction.

    Args:
        regime: Detected market regime.
        direction: "long" or "short".

    Returns:
        Tuple of ATR multipliers for SL, TP1, TP2, TP3.
    """
    if regime == MarketRegime.HIGH_VOLATILITY:
        return _REGIME_MULTIPLIERS["high_volatility"]
    if regime == MarketRegime.RANGING:
        return _REGIME_MULTIPLIERS["ranging"]

    # Trending — check alignment
    if regime == MarketRegime.TRENDING_BULL:
        if direction == "long":
            return _REGIME_MULTIPLIERS["trend_aligned"]
        else:
            return _REGIME_MULTIPLIERS["trend_counter"]
    elif regime == MarketRegime.TRENDING_BEAR:
        if direction == "short":
            return _REGIME_MULTIPLIERS["trend_aligned"]
        else:
            return _REGIME_MULTIPLIERS["trend_counter"]

    # Fallback
    return _REGIME_MULTIPLIERS["ranging"]
