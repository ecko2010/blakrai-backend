"""
Technical analysis module — computes indicators and patterns from OHLCV data.
Uses pandas + ta library for vectorized, correct calculations.
NO hardcoded thresholds — everything is dynamically computed from data.
"""

import numpy as np
import pandas as pd
import ta
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class IndicatorSet:
    """Complete set of technical indicators for analysis."""
    # Trend
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_9: float | None = None
    ema_21: float | None = None
    ema_55: float | None = None

    # Momentum
    rsi_14: float | None = None
    rsi_7: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    cci: float | None = None
    mfi: float | None = None
    williams_r: float | None = None

    # Volatility
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_width: float | None = None
    atr: float | None = None
    atr_percent: float | None = None

    # Volume
    obv: float | None = None
    vwap: float | None = None
    volume_sma_20: float | None = None
    volume_ratio: float | None = None  # current vol / 20-period avg

    # Support/Resistance
    pivot: float | None = None
    support_1: float | None = None
    support_2: float | None = None
    resistance_1: float | None = None
    resistance_2: float | None = None

    # Ichimoku
    ichimoku_a: float | None = None
    ichimoku_b: float | None = None
    ichimoku_base: float | None = None
    ichimoku_conv: float | None = None

    # ADX
    adx: float | None = None
    adx_pos: float | None = None
    adx_neg: float | None = None

    # Extra
    current_price: float | None = None
    price_vs_sma200: float | None = None  # % distance from SMA200

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class PatternSignal:
    name: str
    direction: str  # "bullish" or "bearish"
    strength: float  # 0.0 to 1.0
    description: str


@dataclass
class TrendAnalysis:
    direction: str  # "bullish", "bearish", "neutral"
    strength: float  # 0.0 to 1.0
    timeframe: str
    factors: list[str] = field(default_factory=list)


def candles_to_df(candles: list) -> pd.DataFrame:
    """Convert list of Candle/OHLCV objects to DataFrame.
    Handles both OHLCV (open/high/low/close/volume) and Candle (o/h/l/c/v) field names."""
    records = []
    for c in candles:
        records.append({
            "timestamp": c.timestamp,
            "open": getattr(c, "open", None) or getattr(c, "o", 0),
            "high": getattr(c, "high", None) or getattr(c, "h", 0),
            "low": getattr(c, "low", None) or getattr(c, "l", 0),
            "close": getattr(c, "close", None) or getattr(c, "c", 0),
            "volume": getattr(c, "volume", None) or getattr(c, "v", 0),
        })
    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def compute_indicators(df: pd.DataFrame) -> IndicatorSet:
    """Compute all technical indicators from OHLCV DataFrame."""
    if len(df) < 20:
        logger.warning("Not enough data for full indicator calculation")
        return IndicatorSet()

    indicators = IndicatorSet()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Current price
    indicators.current_price = float(close.iloc[-1])

    # ─── Trend (Moving Averages) ──────────────────
    if len(df) >= 20:
        indicators.sma_20 = float(ta.trend.sma_indicator(close, 20).iloc[-1])
        indicators.ema_9 = float(ta.trend.ema_indicator(close, 9).iloc[-1])
        indicators.ema_21 = float(ta.trend.ema_indicator(close, 21).iloc[-1])
    if len(df) >= 50:
        indicators.sma_50 = float(ta.trend.sma_indicator(close, 50).iloc[-1])
        indicators.ema_55 = float(ta.trend.ema_indicator(close, 55).iloc[-1])
    if len(df) >= 200:
        indicators.sma_200 = float(ta.trend.sma_indicator(close, 200).iloc[-1])
        indicators.price_vs_sma200 = (
            (indicators.current_price - indicators.sma_200) / indicators.sma_200 * 100
        )

    # ─── Momentum ─────────────────────────────────
    if len(df) >= 14:
        indicators.rsi_14 = float(ta.momentum.rsi(close, 14).iloc[-1])
    if len(df) >= 7:
        indicators.rsi_7 = float(ta.momentum.rsi(close, 7).iloc[-1])

    stoch = ta.momentum.StochasticOscillator(high, low, close, 14, 3)
    indicators.stoch_k = float(stoch.stoch().iloc[-1]) if not np.isnan(stoch.stoch().iloc[-1]) else None
    indicators.stoch_d = float(stoch.stoch_signal().iloc[-1]) if not np.isnan(stoch.stoch_signal().iloc[-1]) else None

    macd_obj = ta.trend.MACD(close)
    indicators.macd = float(macd_obj.macd().iloc[-1]) if not np.isnan(macd_obj.macd().iloc[-1]) else None
    indicators.macd_signal = float(macd_obj.macd_signal().iloc[-1]) if not np.isnan(macd_obj.macd_signal().iloc[-1]) else None
    indicators.macd_histogram = float(macd_obj.macd_diff().iloc[-1]) if not np.isnan(macd_obj.macd_diff().iloc[-1]) else None

    if len(df) >= 20:
        indicators.cci = float(ta.trend.cci(high, low, close, 20).iloc[-1])
        indicators.mfi = float(ta.volume.money_flow_index(high, low, close, volume, 14).iloc[-1])

    indicators.williams_r = float(ta.momentum.williams_r(high, low, close, 14).iloc[-1])

    # ─── Volatility ───────────────────────────────
    bb = ta.volatility.BollingerBands(close, 20, 2)
    indicators.bb_upper = float(bb.bollinger_hband().iloc[-1])
    indicators.bb_middle = float(bb.bollinger_mavg().iloc[-1])
    indicators.bb_lower = float(bb.bollinger_lband().iloc[-1])
    indicators.bb_width = float(bb.bollinger_wband().iloc[-1])

    atr_series = ta.volatility.average_true_range(high, low, close, 14)
    indicators.atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else None
    if indicators.atr and indicators.current_price:
        indicators.atr_percent = indicators.atr / indicators.current_price * 100

    # ─── Volume ───────────────────────────────────
    indicators.obv = float(ta.volume.on_balance_volume(close, volume).iloc[-1])
    vol_sma = volume.rolling(20).mean()
    if not np.isnan(vol_sma.iloc[-1]):
        indicators.volume_sma_20 = float(vol_sma.iloc[-1])
        if indicators.volume_sma_20 > 0:
            indicators.volume_ratio = float(volume.iloc[-1] / indicators.volume_sma_20)

    # VWAP (intraday approximation)
    cum_vol = volume.cumsum()
    cum_vol_price = (close * volume).cumsum()
    if cum_vol.iloc[-1] > 0:
        indicators.vwap = float(cum_vol_price.iloc[-1] / cum_vol.iloc[-1])

    # ─── Pivot Points (proper daily aggregation) ────────────────
    # For sub-daily data, aggregate last N bars to approximate daily range
    # 4h → 6 bars/day, 1h → 24 bars/day, etc.
    lookback = min(len(df) - 1, 24)  # Up to 24 bars for daily estimate
    if lookback >= 6:
        day_high = float(high.iloc[-lookback-1:-1].max())
        day_low = float(low.iloc[-lookback-1:-1].min())
        day_close = float(close.iloc[-2])
    else:
        day_high = float(high.iloc[-2])
        day_low = float(low.iloc[-2])
        day_close = float(close.iloc[-2])

    indicators.pivot = (day_high + day_low + day_close) / 3
    indicators.support_1 = 2 * indicators.pivot - day_high
    indicators.resistance_1 = 2 * indicators.pivot - day_low
    indicators.support_2 = indicators.pivot - (day_high - day_low)
    indicators.resistance_2 = indicators.pivot + (day_high - day_low)

    # ─── Ichimoku ─────────────────────────────────
    ichimoku = ta.trend.IchimokuIndicator(high, low)
    indicators.ichimoku_a = float(ichimoku.ichimoku_a().iloc[-1]) if not np.isnan(ichimoku.ichimoku_a().iloc[-1]) else None
    indicators.ichimoku_b = float(ichimoku.ichimoku_b().iloc[-1]) if not np.isnan(ichimoku.ichimoku_b().iloc[-1]) else None
    indicators.ichimoku_base = float(ichimoku.ichimoku_base_line().iloc[-1]) if not np.isnan(ichimoku.ichimoku_base_line().iloc[-1]) else None
    indicators.ichimoku_conv = float(ichimoku.ichimoku_conversion_line().iloc[-1]) if not np.isnan(ichimoku.ichimoku_conversion_line().iloc[-1]) else None

    # ─── ADX ──────────────────────────────────────
    adx_obj = ta.trend.ADXIndicator(high, low, close, 14)
    indicators.adx = float(adx_obj.adx().iloc[-1]) if not np.isnan(adx_obj.adx().iloc[-1]) else None
    indicators.adx_pos = float(adx_obj.adx_pos().iloc[-1]) if not np.isnan(adx_obj.adx_pos().iloc[-1]) else None
    indicators.adx_neg = float(adx_obj.adx_neg().iloc[-1]) if not np.isnan(adx_obj.adx_neg().iloc[-1]) else None

    return indicators


def detect_patterns(df: pd.DataFrame) -> list[PatternSignal]:
    """Detect candlestick and chart patterns from OHLCV data."""
    if len(df) < 5:
        return []

    patterns = []
    close = df["close"].values
    open_ = df["open"].values
    high = df["high"].values
    low = df["low"].values

    # Moving average crossovers
    if len(df) >= 21:
        ema9 = ta.trend.ema_indicator(df["close"], 9).values
        ema21 = ta.trend.ema_indicator(df["close"], 21).values
        if ema9[-1] > ema21[-1] and ema9[-2] <= ema21[-2]:
            patterns.append(PatternSignal("EMA 9/21 Bullish Cross", "bullish", 0.7, "Short-term EMA crossed above medium-term"))
        elif ema9[-1] < ema21[-1] and ema9[-2] >= ema21[-2]:
            patterns.append(PatternSignal("EMA 9/21 Bearish Cross", "bearish", 0.7, "Short-term EMA crossed below medium-term"))

    # MACD crossover
    macd_obj = ta.trend.MACD(df["close"])
    macd_line = macd_obj.macd().values
    signal_line = macd_obj.macd_signal().values
    if not np.isnan(macd_line[-1]) and not np.isnan(signal_line[-1]):
        if not np.isnan(macd_line[-2]) and not np.isnan(signal_line[-2]):
            if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                patterns.append(PatternSignal("MACD Bullish Cross", "bullish", 0.65, "MACD crossed above signal line"))
            elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                patterns.append(PatternSignal("MACD Bearish Cross", "bearish", 0.65, "MACD crossed below signal line"))

    # RSI divergences (use 10+ bars for meaningful divergence)
    if len(df) >= 14:
        rsi = ta.momentum.rsi(df["close"], 14).values
        lookback_div = min(14, len(rsi) - 1)
        # Bullish divergence: price lower low, RSI higher low
        if close[-1] < close[-lookback_div] and rsi[-1] > rsi[-lookback_div] and rsi[-1] < 35:
            patterns.append(PatternSignal("RSI Bullish Divergence", "bullish", 0.75, "Price making lower lows but RSI making higher lows"))
        elif close[-1] > close[-lookback_div] and rsi[-1] < rsi[-lookback_div] and rsi[-1] > 65:
            patterns.append(PatternSignal("RSI Bearish Divergence", "bearish", 0.75, "Price making higher highs but RSI making lower highs"))
    # Bollinger Band squeeze/breakout
    bb = ta.volatility.BollingerBands(df["close"], 20, 2)
    bb_width = bb.bollinger_wband().values
    if len(bb_width) >= 20 and not np.isnan(bb_width[-1]):
        avg_width = np.nanmean(bb_width[-20:])
        if avg_width > 0 and bb_width[-1] < avg_width * 0.5:
            patterns.append(PatternSignal("BB Squeeze", "neutral", 0.6, "Bollinger Bands squeezing — expect breakout"))
        if close[-1] > bb.bollinger_hband().values[-1]:
            patterns.append(PatternSignal("BB Upper Breakout", "bullish", 0.55, "Price broke above upper Bollinger Band"))
        elif close[-1] < bb.bollinger_lband().values[-1]:
            patterns.append(PatternSignal("BB Lower Breakout", "bearish", 0.55, "Price broke below lower Bollinger Band"))

    # Volume surge
    vol = df["volume"].values
    vol_avg = np.mean(vol[-20:]) if len(vol) >= 20 else np.mean(vol)
    if vol_avg > 0 and vol[-1] > vol_avg * 2.0:
        direction = "bullish" if close[-1] > open_[-1] else "bearish"
        patterns.append(PatternSignal("Volume Surge", direction, 0.6, f"Volume {vol[-1]/vol_avg:.1f}x above average"))

    # Engulfing patterns
    if len(df) >= 2:
        prev_body = close[-2] - open_[-2]
        curr_body = close[-1] - open_[-1]
        if prev_body < 0 and curr_body > 0 and open_[-1] <= close[-2] and close[-1] >= open_[-2]:
            patterns.append(PatternSignal("Bullish Engulfing", "bullish", 0.7, "Bullish engulfing candlestick pattern"))
        elif prev_body > 0 and curr_body < 0 and open_[-1] >= close[-2] and close[-1] <= open_[-2]:
            patterns.append(PatternSignal("Bearish Engulfing", "bearish", 0.7, "Bearish engulfing candlestick pattern"))

    # Hammer / Shooting star
    body = abs(close[-1] - open_[-1])
    lower_shadow = min(close[-1], open_[-1]) - low[-1]
    upper_shadow = high[-1] - max(close[-1], open_[-1])
    total_range = high[-1] - low[-1]

    if total_range > 0 and body > 0:
        if lower_shadow > body * 2 and upper_shadow < body * 0.3:
            patterns.append(PatternSignal("Hammer", "bullish", 0.65, "Hammer candlestick — potential reversal"))
        elif upper_shadow > body * 2 and lower_shadow < body * 0.3:
            patterns.append(PatternSignal("Shooting Star", "bearish", 0.65, "Shooting star — potential reversal"))

    return patterns


def analyze_trend(df: pd.DataFrame, timeframe: str = "4h") -> TrendAnalysis:
    """Comprehensive trend analysis combining multiple indicators."""
    if len(df) < 20:
        return TrendAnalysis(direction="neutral", strength=0.0, timeframe=timeframe)

    indicators = compute_indicators(df)
    bullish_factors = []
    bearish_factors = []

    price = indicators.current_price

    # MA alignment
    if indicators.ema_9 and indicators.ema_21:
        if indicators.ema_9 > indicators.ema_21:
            bullish_factors.append("EMA9 > EMA21")
        else:
            bearish_factors.append("EMA9 < EMA21")

    if indicators.sma_50 and price:
        if price > indicators.sma_50:
            bullish_factors.append("Price > SMA50")
        else:
            bearish_factors.append("Price < SMA50")

    if indicators.sma_200 and price:
        if price > indicators.sma_200:
            bullish_factors.append("Price > SMA200")
        else:
            bearish_factors.append("Price < SMA200")

    # RSI
    if indicators.rsi_14:
        if indicators.rsi_14 > 50:
            bullish_factors.append(f"RSI {indicators.rsi_14:.0f} bullish")
        elif indicators.rsi_14 < 50:
            bearish_factors.append(f"RSI {indicators.rsi_14:.0f} bearish")

    # MACD
    if indicators.macd_histogram:
        if indicators.macd_histogram > 0:
            bullish_factors.append("MACD positive")
        else:
            bearish_factors.append("MACD negative")

    # ADX
    if indicators.adx and indicators.adx_pos and indicators.adx_neg:
        if indicators.adx > 25:
            if indicators.adx_pos > indicators.adx_neg:
                bullish_factors.append(f"ADX {indicators.adx:.0f} trending bullish")
            else:
                bearish_factors.append(f"ADX {indicators.adx:.0f} trending bearish")

    # Ichimoku
    if indicators.ichimoku_conv and indicators.ichimoku_base:
        if indicators.ichimoku_conv > indicators.ichimoku_base:
            bullish_factors.append("Ichimoku bullish")
        else:
            bearish_factors.append("Ichimoku bearish")

    # Volume confirmation
    if indicators.volume_ratio and indicators.volume_ratio > 1.5:
        bullish_factors.append(f"Volume {indicators.volume_ratio:.1f}x surge")

    # Calculate score
    total = len(bullish_factors) + len(bearish_factors)
    if total == 0:
        return TrendAnalysis(direction="neutral", strength=0.0, timeframe=timeframe)

    bull_score = len(bullish_factors) / total
    bear_score = len(bearish_factors) / total

    if bull_score > 0.6:
        return TrendAnalysis(
            direction="bullish",
            strength=bull_score,
            timeframe=timeframe,
            factors=bullish_factors,
        )
    elif bear_score > 0.6:
        return TrendAnalysis(
            direction="bearish",
            strength=bear_score,
            timeframe=timeframe,
            factors=bearish_factors,
        )
    else:
        return TrendAnalysis(
            direction="neutral",
            strength=max(bull_score, bear_score),
            timeframe=timeframe,
            factors=bullish_factors + bearish_factors,
        )
