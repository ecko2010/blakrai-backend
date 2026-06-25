"""
Test technical analysis — indicator computation and pattern detection.
"""

import numpy as np
import pandas as pd
import pytest

from app.signals.analyzer import (
    IndicatorSet, PatternSignal, TrendAnalysis,
    compute_indicators, detect_patterns, candles_to_df,
)


def _make_ohlcv_df(periods: int = 200, trend: str = "up") -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing indicators."""
    np.random.seed(42)
    base_price = 100.0
    prices = [base_price]
    for i in range(1, periods):
        change = np.random.normal(0.001 if trend == "up" else -0.001, 0.02)
        prices.append(prices[-1] * (1 + change))

    prices = np.array(prices)
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, periods)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, periods)))
    opens = np.roll(prices, 1)
    opens[0] = prices[0]
    volumes = np.random.uniform(1e6, 1e7, periods)

    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=periods, freq="4h"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
    })
    return df


class TestIndicatorSet:
    def test_to_dict_excludes_none(self):
        ind = IndicatorSet(rsi_14=50.0)
        d = ind.to_dict()
        assert "rsi_14" in d
        assert d["rsi_14"] == 50.0
        # None fields should be absent
        assert "sma_200" not in d

    def test_default_all_none(self):
        ind = IndicatorSet()
        d = ind.to_dict()
        assert len(d) == 0


class TestComputeIndicators:
    def test_basic_compute(self):
        df = _make_ohlcv_df(200)
        ind = compute_indicators(df)
        assert ind.current_price is not None
        assert ind.rsi_14 is not None
        assert 0 <= ind.rsi_14 <= 100
        assert ind.sma_20 is not None
        assert ind.sma_50 is not None
        assert ind.sma_200 is not None
        assert ind.macd is not None
        assert ind.bb_upper is not None
        assert ind.bb_lower is not None
        assert ind.atr is not None

    def test_short_data_returns_partial(self):
        df = _make_ohlcv_df(25)
        ind = compute_indicators(df)
        # Should compute some but not all
        assert ind.current_price is not None
        assert ind.sma_20 is not None
        # Not enough data for SMA200
        assert ind.sma_200 is None

    def test_very_short_data_returns_empty(self):
        df = _make_ohlcv_df(10)
        ind = compute_indicators(df)
        # Should return empty indicator set without crashing
        assert isinstance(ind, IndicatorSet)


class TestDetectPatterns:
    def test_returns_list_of_patterns(self):
        df = _make_ohlcv_df(200)
        ind = compute_indicators(df)
        patterns = detect_patterns(df, ind)
        assert isinstance(patterns, list)
        for p in patterns:
            assert isinstance(p, PatternSignal)
            assert p.direction in ("bullish", "bearish", "neutral")
            assert 0 <= p.strength <= 1.0


class TestCandlesToDf:
    def test_converts_ohlcv_objects(self):
        class FakeCandle:
            def __init__(self, ts, o, h, l, c, v):
                self.timestamp = ts
                self.open = o
                self.high = h
                self.low = l
                self.close = c
                self.volume = v

        candles = [
            FakeCandle(1000, 100, 105, 95, 102, 1e6),
            FakeCandle(2000, 102, 108, 100, 106, 1.5e6),
        ]
        df = candles_to_df(candles)
        assert len(df) == 2
        assert "close" in df.columns
        assert df["close"].iloc[0] == 102
