"""
Cross-exchange correlation analysis.
Detects correlation patterns, divergences, and confirms signals across exchanges.
"""

import asyncio
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from loguru import logger

from app.exchanges.manager import exchange_manager
from app.signals.analyzer import candles_to_df


@dataclass
class CorrelationResult:
    symbol: str
    exchanges_analyzed: list[str]
    price_correlation: float  # -1.0 to 1.0
    volume_correlation: float
    price_divergence_pct: float
    volume_divergence_pct: float
    consensus_direction: str  # "bullish", "bearish", "mixed"
    confidence_boost: float  # additional confidence from cross-exchange confirmation
    details: dict = field(default_factory=dict)


@dataclass
class MarketCorrelation:
    btc_correlation: float | None = None
    eth_correlation: float | None = None
    sector_correlation: dict = field(default_factory=dict)
    macro_correlation: float | None = None


async def analyze_cross_exchange_correlation(
    symbol: str, interval: str = "4h", limit: int = 100
) -> CorrelationResult:
    """Analyze price/volume correlation across all exchanges for a symbol."""
    candle_sets = await exchange_manager.get_candles_all_exchanges(symbol, interval, limit)

    # Filter out exchanges with insufficient data
    valid_exchanges = {
        name: candles for name, candles in candle_sets.items()
        if len(candles) >= 20
    }

    if len(valid_exchanges) < 2:
        return CorrelationResult(
            symbol=symbol,
            exchanges_analyzed=list(valid_exchanges.keys()),
            price_correlation=1.0,
            volume_correlation=1.0,
            price_divergence_pct=0.0,
            volume_divergence_pct=0.0,
            consensus_direction="neutral",
            confidence_boost=0.0,
        )

    # Build aligned DataFrames
    dfs = {}
    for name, candles in valid_exchanges.items():
        df = candles_to_df(candles)
        df = df.set_index("timestamp")
        dfs[name] = df

    # Align by timestamp
    exchange_names = list(dfs.keys())
    close_prices = pd.DataFrame({name: dfs[name]["close"] for name in exchange_names})
    close_prices = close_prices.dropna()

    volumes = pd.DataFrame({name: dfs[name]["volume"] for name in exchange_names})
    volumes = volumes.dropna()

    # Compute correlations
    price_corr_matrix = close_prices.corr()
    volume_corr_matrix = volumes.corr()

    # Average correlation (excluding diagonal)
    n = len(exchange_names)
    if n > 1:
        price_corr_values = []
        volume_corr_values = []
        for i in range(n):
            for j in range(i + 1, n):
                pc = price_corr_matrix.iloc[i, j]
                vc = volume_corr_matrix.iloc[i, j]
                if not np.isnan(pc):
                    price_corr_values.append(pc)
                if not np.isnan(vc):
                    volume_corr_values.append(vc)
        avg_price_corr = float(np.mean(price_corr_values)) if price_corr_values else 1.0
        avg_volume_corr = float(np.mean(volume_corr_values)) if volume_corr_values else 1.0
    else:
        avg_price_corr = 1.0
        avg_volume_corr = 1.0

    # Price divergence (max difference between last prices)
    last_prices = {name: float(close_prices[name].iloc[-1]) for name in exchange_names if len(close_prices[name]) > 0}
    if last_prices:
        max_p = max(last_prices.values())
        min_p = min(last_prices.values())
        price_div = ((max_p - min_p) / min_p * 100) if min_p > 0 else 0.0
    else:
        price_div = 0.0

    # Volume divergence
    last_volumes = {name: float(volumes[name].iloc[-1]) for name in exchange_names if len(volumes[name]) > 0}
    if last_volumes:
        max_v = max(last_volumes.values())
        min_v = min(last_volumes.values())
        vol_div = ((max_v - min_v) / max_v * 100) if max_v > 0 else 0.0
    else:
        vol_div = 0.0

    # Consensus direction from price changes
    directions = {}
    for name in exchange_names:
        if len(close_prices[name]) >= 2:
            change = close_prices[name].iloc[-1] - close_prices[name].iloc[-5] if len(close_prices[name]) >= 5 else close_prices[name].iloc[-1] - close_prices[name].iloc[-2]
            directions[name] = "bullish" if change > 0 else "bearish"

    bullish_count = sum(1 for d in directions.values() if d == "bullish")
    bearish_count = sum(1 for d in directions.values() if d == "bearish")

    if bullish_count > bearish_count:
        consensus = "bullish"
    elif bearish_count > bullish_count:
        consensus = "bearish"
    else:
        consensus = "mixed"

    # Confidence boost: high correlation + agreement = higher confidence
    confidence_boost = 0.0
    if avg_price_corr > 0.95 and consensus != "mixed":
        confidence_boost = 0.15
    elif avg_price_corr > 0.85 and consensus != "mixed":
        confidence_boost = 0.10
    elif avg_price_corr > 0.7:
        confidence_boost = 0.05

    return CorrelationResult(
        symbol=symbol,
        exchanges_analyzed=exchange_names,
        price_correlation=round(avg_price_corr, 4),
        volume_correlation=round(avg_volume_corr, 4),
        price_divergence_pct=round(price_div, 4),
        volume_divergence_pct=round(vol_div, 4),
        consensus_direction=consensus,
        confidence_boost=confidence_boost,
        details={
            "last_prices": last_prices,
            "last_volumes": last_volumes,
            "directions": directions,
        },
    )


async def compute_btc_correlation(symbol: str, interval: str = "4h", limit: int = 100) -> float | None:
    """Compute correlation of a coin's price with BTC."""
    try:
        candle_sets = await exchange_manager.get_candles_all_exchanges(symbol, interval, limit)
        btc_candles_sets = await exchange_manager.get_candles_all_exchanges("BTCUSDT", interval, limit)

        # Take first available exchange data
        coin_candles = None
        btc_candles = None
        for candles in candle_sets.values():
            if len(candles) >= 20:
                coin_candles = candles
                break
        for candles in btc_candles_sets.values():
            if len(candles) >= 20:
                btc_candles = candles
                break

        if not coin_candles or not btc_candles:
            return None

        coin_df = candles_to_df(coin_candles).set_index("timestamp")
        btc_df = candles_to_df(btc_candles).set_index("timestamp")

        # Align
        merged = pd.DataFrame({
            "coin": coin_df["close"],
            "btc": btc_df["close"],
        }).dropna()

        if len(merged) < 10:
            return None

        # Returns correlation
        coin_returns = merged["coin"].pct_change().dropna()
        btc_returns = merged["btc"].pct_change().dropna()

        corr = float(coin_returns.corr(btc_returns))
        return round(corr, 4) if not np.isnan(corr) else None
    except Exception as e:
        logger.debug(f"BTC correlation failed for {symbol}: {e}")
        return None
        return None
