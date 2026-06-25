"""
Feature extraction pipeline for ML quality gate.
Extracts numeric features from IndicatorSet, cross-exchange data, and volume.
Uses scipy for anomaly detection (z-score).
"""

import numpy as np
from scipy import stats
from loguru import logger

from app.signals.analyzer import IndicatorSet
from app.signals.correlation import CorrelationResult


def extract_features(
    indicators: IndicatorSet,
    correlation: CorrelationResult | None = None,
    volume_history: list[float] | None = None,
    exchange_score: float = 0.5,
    direction: str = "long",
) -> dict[str, float]:
    """Extract a flat feature vector for ML model.

    Returns dict[str, float] with ~30 features.
    All values are numeric (float), safe for LightGBM.
    """
    f: dict[str, float] = {}

    # ── Technical indicators ──────────────────────
    f["rsi_14"] = indicators.rsi_14 or 50.0
    f["rsi_7"] = indicators.rsi_7 or 50.0
    f["macd_histogram"] = indicators.macd_histogram or 0.0
    f["adx"] = indicators.adx or 0.0
    f["atr_pct"] = indicators.atr_percent or 0.0
    f["bb_width"] = indicators.bb_width or 0.0
    f["volume_ratio"] = indicators.volume_ratio or 1.0
    f["stoch_k"] = indicators.stoch_k or 50.0
    f["stoch_d"] = indicators.stoch_d or 50.0
    f["cci"] = indicators.cci or 0.0
    f["mfi"] = indicators.mfi or 50.0
    f["williams_r"] = indicators.williams_r or -50.0

    # ── Price context ─────────────────────────────
    if indicators.current_price and indicators.sma_200:
        f["price_vs_sma200"] = (indicators.current_price / indicators.sma_200 - 1) * 100
    else:
        f["price_vs_sma200"] = 0.0

    if indicators.current_price and indicators.sma_50:
        f["price_vs_sma50"] = (indicators.current_price / indicators.sma_50 - 1) * 100
    else:
        f["price_vs_sma50"] = 0.0

    if indicators.current_price and indicators.ema_21:
        f["price_vs_ema21"] = (indicators.current_price / indicators.ema_21 - 1) * 100
    else:
        f["price_vs_ema21"] = 0.0

    # ── Trend strength ────────────────────────────
    f["adx_pos"] = indicators.adx_pos or 0.0
    f["adx_neg"] = indicators.adx_neg or 0.0
    f["adx_diff"] = (indicators.adx_pos or 0) - (indicators.adx_neg or 0)

    # ── Direction encoding ────────────────────────
    f["is_long"] = 1.0 if direction == "long" else 0.0

    # ── RSI zone (relative to direction) ──────────
    rsi = indicators.rsi_14 or 50.0
    if direction == "long":
        f["rsi_zone"] = 1.0 if 30 <= rsi <= 60 else (0.5 if rsi < 30 else 0.0)
    else:
        f["rsi_zone"] = 1.0 if 40 <= rsi <= 70 else (0.5 if rsi > 70 else 0.0)

    # ── Cross-exchange features ───────────────────
    if correlation:
        f["price_correlation"] = correlation.price_correlation
        f["volume_correlation"] = correlation.volume_correlation
        f["price_divergence"] = correlation.price_divergence_pct
        f["volume_divergence"] = correlation.volume_divergence_pct
        f["n_exchanges"] = float(len(correlation.exchanges_analyzed))
        f["cross_confidence_boost"] = correlation.confidence_boost
        f["consensus_aligned"] = 1.0 if (
            (direction == "long" and correlation.consensus_direction == "bullish")
            or (direction == "short" and correlation.consensus_direction == "bearish")
        ) else 0.0
    else:
        f["price_correlation"] = 1.0
        f["volume_correlation"] = 1.0
        f["price_divergence"] = 0.0
        f["volume_divergence"] = 0.0
        f["n_exchanges"] = 1.0
        f["cross_confidence_boost"] = 0.0
        f["consensus_aligned"] = 0.0

    # ── Exchange quality ──────────────────────────
    f["exchange_score"] = exchange_score

    # ── Volume anomaly (scipy z-score) ────────────
    f["volume_zscore"] = 0.0
    if volume_history and len(volume_history) >= 20:
        try:
            zscores = stats.zscore(volume_history)
            last_z = float(zscores[-1])
            if not np.isnan(last_z):
                f["volume_zscore"] = last_z
        except Exception:
            pass

    return f


# ── Feature names (sorted, stable order for ML model) ──

FEATURE_NAMES = sorted([
    "rsi_14", "rsi_7", "macd_histogram", "adx", "atr_pct", "bb_width",
    "volume_ratio", "stoch_k", "stoch_d", "cci", "mfi", "williams_r",
    "price_vs_sma200", "price_vs_sma50", "price_vs_ema21",
    "adx_pos", "adx_neg", "adx_diff", "is_long", "rsi_zone",
    "price_correlation", "volume_correlation", "price_divergence",
    "volume_divergence", "n_exchanges", "cross_confidence_boost",
    "consensus_aligned", "exchange_score", "volume_zscore",
])


# ── Anomaly detection ────────────────────────────

def detect_volume_anomaly(volumes: list[float], threshold: float = 3.0) -> tuple[bool, float]:
    """Detect anomalous volume using scipy z-score.

    Returns (is_anomaly, z_score_value).
    """
    if len(volumes) < 20:
        return False, 0.0
    try:
        zscores = stats.zscore(volumes)
        last_z = float(zscores[-1])
        if np.isnan(last_z):
            return False, 0.0
        return abs(last_z) > threshold, last_z
    except Exception:
        return False, 0.0


def detect_spread_anomaly(spreads: list[float], threshold: float = 2.5) -> tuple[bool, float]:
    """Detect abnormal spread widening across exchanges.

    Returns (is_anomaly, max_z_score).
    """
    if len(spreads) < 5:
        return False, 0.0
    try:
        zscores = stats.zscore(spreads)
        max_z = float(np.max(np.abs(zscores)))
        if np.isnan(max_z):
            return False, 0.0
        return max_z > threshold, max_z
    except Exception:
        return False, 0.0
