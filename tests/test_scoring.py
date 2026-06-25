"""
Test signal scoring — ScoreBreakdown, compute_signal_score.
"""

import pytest
from app.signals.analyzer import IndicatorSet, TrendAnalysis, PatternSignal
from app.signals.scoring import compute_signal_score, ScoreBreakdown


def _make_indicators(**overrides) -> IndicatorSet:
    """Helper to create an IndicatorSet with sensible defaults."""
    defaults = {
        "rsi_14": 45.0,
        "macd_histogram": 0.5,
        "stoch_k": 55.0,
        "stoch_d": 50.0,
        "cci": 50.0,
        "mfi": 60.0,
        "williams_r": -40.0,
        "adx": 30.0,
        "adx_pos": 25.0,
        "adx_neg": 15.0,
        "volume_ratio": 1.5,
        "current_price": 100.0,
        "bb_upper": 105.0,
        "bb_lower": 95.0,
        "bb_middle": 100.0,
    }
    defaults.update(overrides)
    return IndicatorSet(**defaults)


def _make_trend(direction: str = "bullish", strength: float = 0.7) -> TrendAnalysis:
    return TrendAnalysis(direction=direction, strength=strength, timeframe="4h", factors=[])


class TestScoreBreakdown:
    def test_default_values(self):
        b = ScoreBreakdown()
        assert b.total == 0.0
        assert b.technical_score == 0.0
        assert isinstance(b.components, dict)


class TestComputeSignalScore:
    def test_returns_score_breakdown(self):
        indicators = _make_indicators()
        trend = _make_trend()
        result = compute_signal_score(
            indicators=indicators,
            trend=trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        assert isinstance(result, ScoreBreakdown)
        assert 0 <= result.total <= 1.0

    def test_long_bullish_scores_higher_than_bearish(self):
        indicators = _make_indicators()
        bullish_trend = _make_trend("bullish", 0.8)
        bearish_trend = _make_trend("bearish", 0.8)

        score_bull = compute_signal_score(
            indicators=indicators,
            trend=bullish_trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        score_bear = compute_signal_score(
            indicators=indicators,
            trend=bearish_trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        assert score_bull.total >= score_bear.total

    def test_high_rr_scores_higher(self):
        indicators = _make_indicators()
        trend = _make_trend()

        # RR 1:2
        score_low_rr = compute_signal_score(
            indicators=indicators,
            trend=trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        # RR 1:4
        score_high_rr = compute_signal_score(
            indicators=indicators,
            trend=trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=120.0,
        )
        assert score_high_rr.risk_reward_score >= score_low_rr.risk_reward_score

    def test_patterns_increase_score(self):
        indicators = _make_indicators()
        trend = _make_trend()

        score_no_patterns = compute_signal_score(
            indicators=indicators,
            trend=trend,
            patterns=[],
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        patterns = [
            PatternSignal(name="EMA bullish cross", direction="bullish", strength=0.8, description="test"),
            PatternSignal(name="MACD bullish cross", direction="bullish", strength=0.7, description="test"),
        ]
        score_with_patterns = compute_signal_score(
            indicators=indicators,
            trend=trend,
            patterns=patterns,
            correlation=None,
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            tp1=110.0,
        )
        assert score_with_patterns.total >= score_no_patterns.total

    def test_score_capped_at_one(self):
        """Even with all perfect inputs, total should not exceed 1.0."""
        indicators = _make_indicators(
            rsi_14=45, macd_histogram=1.0, stoch_k=80, stoch_d=70,
            cci=150, mfi=80, williams_r=-20, adx=40, adx_pos=30, adx_neg=10,
            volume_ratio=3.0,
        )
        trend = _make_trend("bullish", 1.0)
        patterns = [PatternSignal(name=f"p{i}", direction="bullish", strength=1.0, description="") for i in range(5)]

        result = compute_signal_score(
            indicators=indicators, trend=trend, patterns=patterns,
            correlation=None, direction="long",
            entry_price=100.0, stop_loss=97.0, tp1=115.0, tp2=130.0, tp3=150.0,
        )
        assert result.total <= 1.0
