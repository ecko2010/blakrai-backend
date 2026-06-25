"""
Signal scoring — computes a composite confidence score from multiple factors.
Dynamic weights, no hardcoded biases.
"""

from dataclasses import dataclass, field
from app.signals.analyzer import IndicatorSet, TrendAnalysis, PatternSignal
from app.signals.correlation import CorrelationResult


@dataclass
class ScoreBreakdown:
    technical_score: float = 0.0
    pattern_score: float = 0.0
    trend_score: float = 0.0
    correlation_score: float = 0.0
    volume_score: float = 0.0
    risk_reward_score: float = 0.0
    total: float = 0.0
    components: dict = field(default_factory=dict)


def compute_signal_score(
    indicators: IndicatorSet,
    trend: TrendAnalysis,
    patterns: list[PatternSignal],
    correlation: CorrelationResult | None,
    direction: str,
    entry_price: float,
    stop_loss: float,
    tp1: float,
    tp2: float | None = None,
    tp3: float | None = None,
) -> ScoreBreakdown:
    """Compute a composite signal confidence score."""
    breakdown = ScoreBreakdown()

    # ─── TECHNICAL SCORE (0-1) based on indicator alignment ───
    tech_points = 0
    tech_total = 0

    # RSI
    if indicators.rsi_14 is not None:
        tech_total += 1
        if direction == "long":
            if 30 <= indicators.rsi_14 <= 60:
                tech_points += 1.0  # Ideal zone for long entry
            elif 60 < indicators.rsi_14 <= 70:
                tech_points += 0.5
        else:
            if 40 <= indicators.rsi_14 <= 70:
                tech_points += 1.0
            elif 30 <= indicators.rsi_14 < 40:
                tech_points += 0.5

    # MACD
    if indicators.macd_histogram is not None:
        tech_total += 1
        if direction == "long" and indicators.macd_histogram > 0:
            tech_points += 1.0
        elif direction == "short" and indicators.macd_histogram < 0:
            tech_points += 1.0

    # Stochastic — check direction AND zone
    if indicators.stoch_k is not None and indicators.stoch_d is not None:
        tech_total += 1
        if direction == "long" and indicators.stoch_k > indicators.stoch_d and indicators.stoch_k < 80:
            tech_points += 1.0
        elif direction == "short" and indicators.stoch_k < indicators.stoch_d and indicators.stoch_k > 20:
            tech_points += 1.0
        elif direction == "long" and indicators.stoch_k > indicators.stoch_d:
            tech_points += 0.3  # Right direction but overbought zone
        elif direction == "short" and indicators.stoch_k < indicators.stoch_d:
            tech_points += 0.3  # Right direction but oversold zone

    # CCI
    if indicators.cci is not None:
        tech_total += 1
        if direction == "long" and indicators.cci > -100:
            tech_points += 0.5 + min(0.5, indicators.cci / 200)
        elif direction == "short" and indicators.cci < 100:
            tech_points += 0.5 + min(0.5, -indicators.cci / 200)

    # MFI
    if indicators.mfi is not None:
        tech_total += 1
        if direction == "long" and indicators.mfi > 40:
            tech_points += 1.0
        elif direction == "short" and indicators.mfi < 60:
            tech_points += 1.0

    breakdown.technical_score = round(tech_points / tech_total, 4) if tech_total > 0 else 0.5
    breakdown.components["technical"] = {"points": tech_points, "total": tech_total}

    # ─── PATTERN SCORE ────────────────────────────────────
    if patterns:
        aligned_patterns = [p for p in patterns if p.direction == ("bullish" if direction == "long" else "bearish")]
        contrary_patterns = [p for p in patterns if p.direction == ("bearish" if direction == "long" else "bullish")]

        positive = sum(p.strength for p in aligned_patterns)
        negative = sum(p.strength for p in contrary_patterns)

        if positive + negative > 0:
            raw = positive / (positive + negative)
            # Extra penalty: if ANY contrary patterns exist, cap score at 0.4
            if contrary_patterns:
                raw = min(raw, 0.4)
            breakdown.pattern_score = round(raw, 4)
        else:
            breakdown.pattern_score = 0.5

        breakdown.components["patterns"] = {
            "aligned": [p.name for p in aligned_patterns],
            "contrary": [p.name for p in contrary_patterns],
        }
    else:
        breakdown.pattern_score = 0.4  # No patterns = slightly below neutral

    # ─── TREND SCORE ──────────────────────────────────────
    if trend.direction == ("bullish" if direction == "long" else "bearish"):
        breakdown.trend_score = round(0.5 + trend.strength * 0.5, 4)
    elif trend.direction == "neutral":
        breakdown.trend_score = 0.4
    else:
        breakdown.trend_score = round(max(0.1, 0.5 - trend.strength * 0.5), 4)

    breakdown.components["trend"] = {"direction": trend.direction, "strength": trend.strength}

    # ─── CORRELATION SCORE ────────────────────────────────
    if correlation:
        if correlation.consensus_direction == ("bullish" if direction == "long" else "bearish"):
            breakdown.correlation_score = round(0.6 + correlation.confidence_boost, 4)
        elif correlation.consensus_direction == "mixed":
            breakdown.correlation_score = 0.4
        else:
            breakdown.correlation_score = 0.2
    else:
        breakdown.correlation_score = 0.5

    # ─── VOLUME SCORE ─────────────────────────────────────
    if indicators.volume_ratio is not None:
        if indicators.volume_ratio >= 2.0:
            breakdown.volume_score = 1.0
        elif indicators.volume_ratio >= 1.2:
            breakdown.volume_score = 0.8
        elif indicators.volume_ratio >= 0.8:
            breakdown.volume_score = 0.6
        elif indicators.volume_ratio >= 0.65:
            breakdown.volume_score = 0.3
        else:
            # Below 0.65 should already be blocked by filter, but score 0 anyway
            breakdown.volume_score = 0.1
    else:
        breakdown.volume_score = 0.5

    # ─── RISK/REWARD SCORE ────────────────────────────────
    if direction == "long":
        risk = abs(entry_price - stop_loss)
        reward1 = abs(tp1 - entry_price)
    else:
        risk = abs(stop_loss - entry_price)
        reward1 = abs(entry_price - tp1)

    rr_ratio = reward1 / risk if risk > 0 else 0

    if rr_ratio >= 3.0:
        breakdown.risk_reward_score = 1.0
    elif rr_ratio >= 2.0:
        breakdown.risk_reward_score = 0.85
    elif rr_ratio >= 1.5:
        breakdown.risk_reward_score = 0.7
    elif rr_ratio >= 1.2:
        breakdown.risk_reward_score = 0.55
    elif rr_ratio >= 1.0:
        breakdown.risk_reward_score = 0.35
    else:
        breakdown.risk_reward_score = 0.1

    breakdown.components["risk_reward"] = {"ratio": round(rr_ratio, 2)}

    # ─── COMPOSITE TOTAL (weighted average) ───────────────
    # Volume and trend are the strongest discriminators between wins and losses
    weights = {
        "technical": 0.20,
        "pattern": 0.10,
        "trend": 0.25,
        "correlation": 0.10,
        "volume": 0.20,
        "risk_reward": 0.15,
    }

    breakdown.total = round(
        breakdown.technical_score * weights["technical"]
        + breakdown.pattern_score * weights["pattern"]
        + breakdown.trend_score * weights["trend"]
        + breakdown.correlation_score * weights["correlation"]
        + breakdown.volume_score * weights["volume"]
        + breakdown.risk_reward_score * weights["risk_reward"],
        4,
    )

    return breakdown
