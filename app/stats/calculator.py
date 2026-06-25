"""
Statistics calculator — computes all trading metrics correctly.
Handles partial TP hits properly, Sharpe/Sortino/Profit Factor/etc.
"""

import numpy as np
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from sqlalchemy import select, and_, func, or_
from loguru import logger

from app.database import async_session
from app.models import Signal, SignalStatus, SignalDirection


@dataclass
class SignalStats:
    period: str
    total: int = 0
    active: int = 0
    wins: int = 0
    losses: int = 0
    partial_wins: int = 0  # TP1 hit but later SL hit — NOT a loss!
    expired: int = 0

    tp1_hits: int = 0
    tp2_hits: int = 0
    tp3_hits: int = 0

    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_pnl: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0

    tp1_hit_rate: float = 0.0
    tp2_hit_rate: float = 0.0
    tp3_hit_rate: float = 0.0

    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_holding_hours: float = 0.0
    expectancy: float = 0.0

    win_streak: int = 0
    loss_streak: int = 0
    current_streak: int = 0
    current_streak_type: str = ""

    longs_count: int = 0
    shorts_count: int = 0
    longs_win_rate: float = 0.0
    shorts_win_rate: float = 0.0


async def compute_stats(
    period_days: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SignalStats:
    """Compute comprehensive stats for a given period."""

    if period_days:
        period_label = f"Last {period_days} days"
        start = datetime.now(timezone.utc) - timedelta(days=period_days)
        end = datetime.now(timezone.utc)
    elif start_date and end_date:
        period_label = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        start = start_date
        end = end_date
    else:
        period_label = "All time"
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime.now(timezone.utc)

    stats = SignalStats(period=period_label)

    async with async_session() as session:
        # Fetch all signals in period
        result = await session.execute(
            select(Signal).where(
                and_(Signal.created_at >= start, Signal.created_at <= end)
            ).order_by(Signal.created_at)
        )
        signals = result.scalars().all()

    if not signals:
        return stats

    stats.total = len(signals)
    stats.active = sum(1 for s in signals if s.status == SignalStatus.ACTIVE)

    # Categorize results
    closed_signals = [s for s in signals if s.status != SignalStatus.ACTIVE]
    pnl_values = []

    for s in closed_signals:
        pnl = s.pnl_percent or 0

        if s.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT):
            stats.wins += 1
            if s.status == SignalStatus.TP1_HIT:
                stats.tp1_hits += 1
            elif s.status == SignalStatus.TP2_HIT:
                stats.tp2_hits += 1
            elif s.status == SignalStatus.TP3_HIT:
                stats.tp3_hits += 1
        elif s.status == SignalStatus.STOPPED:
            stats.losses += 1
        elif s.status == SignalStatus.CLOSED:
            # Closed with partial TP = partial win
            if pnl > 0:
                stats.partial_wins += 1
                stats.wins += 1  # Count as win since net positive
            else:
                stats.losses += 1
        elif s.status == SignalStatus.EXPIRED:
            stats.expired += 1
            if pnl > 0:
                stats.wins += 1
            elif pnl < 0:
                stats.losses += 1

        pnl_values.append(pnl)

        # Direction stats
        if s.direction == SignalDirection.LONG:
            stats.longs_count += 1
        else:
            stats.shorts_count += 1

    total_closed = stats.wins + stats.losses

    # Win rate (correct: partial wins count as wins)
    if total_closed > 0:
        stats.win_rate = round(stats.wins / total_closed * 100, 1)

    # TP hit rates (based on all closed signals including SL hits)
    if total_closed > 0:
        stats.tp1_hit_rate = round(stats.tp1_hits / total_closed * 100, 1)
        stats.tp2_hit_rate = round(stats.tp2_hits / total_closed * 100, 1)
        stats.tp3_hit_rate = round(stats.tp3_hits / total_closed * 100, 1)

    # PnL calculations
    if pnl_values:
        winning_pnls = [p for p in pnl_values if p > 0]
        losing_pnls = [p for p in pnl_values if p < 0]

        stats.total_pnl = round(sum(pnl_values), 2)
        stats.best_trade = round(max(pnl_values), 2) if pnl_values else 0
        stats.worst_trade = round(min(pnl_values), 2) if pnl_values else 0
        stats.avg_win = round(np.mean(winning_pnls), 2) if winning_pnls else 0
        stats.avg_loss = round(np.mean(losing_pnls), 2) if losing_pnls else 0

        # Profit Factor
        gross_profit = sum(winning_pnls) if winning_pnls else 0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0
        stats.profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        # Sharpe Ratio (annualized assuming daily signals)
        if len(pnl_values) >= 2:
            returns = np.array(pnl_values) / 100
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            if std_return > 0:
                stats.sharpe_ratio = round(mean_return / std_return * np.sqrt(365), 2)

        # Sortino Ratio (only downside deviation)
        if len(pnl_values) >= 2:
            returns = np.array(pnl_values) / 100
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_dev = np.std(negative_returns, ddof=1)
                if downside_dev > 0:
                    stats.sortino_ratio = round(np.mean(returns) / downside_dev * np.sqrt(365), 2)

        # Max Drawdown (sequential)
        cumulative = np.cumsum(pnl_values)
        peak = np.maximum.accumulate(cumulative)
        drawdown = cumulative - peak
        stats.max_drawdown = round(float(np.min(drawdown)), 2) if len(drawdown) > 0 else 0

        # Expectancy
        if total_closed > 0:
            stats.expectancy = round(stats.total_pnl / total_closed, 2)

    # Streaks
    current_streak = 0
    current_type = ""
    max_win_streak = 0
    max_loss_streak = 0
    temp_win = 0
    temp_loss = 0

    for s in closed_signals:
        pnl = s.pnl_percent or 0
        if pnl > 0:
            temp_win += 1
            temp_loss = 0
            max_win_streak = max(max_win_streak, temp_win)
            current_streak = temp_win
            current_type = "win"
        elif pnl < 0:
            temp_loss += 1
            temp_win = 0
            max_loss_streak = max(max_loss_streak, temp_loss)
            current_streak = temp_loss
            current_type = "loss"

    stats.win_streak = max_win_streak
    stats.loss_streak = max_loss_streak
    stats.current_streak = current_streak
    stats.current_streak_type = current_type

    # Direction-specific win rates
    long_wins = sum(
        1 for s in closed_signals
        if s.direction == SignalDirection.LONG and (s.pnl_percent or 0) > 0
    )
    short_wins = sum(
        1 for s in closed_signals
        if s.direction == SignalDirection.SHORT and (s.pnl_percent or 0) > 0
    )
    long_closed = sum(1 for s in closed_signals if s.direction == SignalDirection.LONG)
    short_closed = sum(1 for s in closed_signals if s.direction == SignalDirection.SHORT)

    stats.longs_win_rate = round(long_wins / long_closed * 100, 1) if long_closed > 0 else 0
    stats.shorts_win_rate = round(short_wins / short_closed * 100, 1) if short_closed > 0 else 0

    # Average holding time
    holding_times = []
    for s in closed_signals:
        if s.closed_at and s.created_at:
            hours = (s.closed_at - s.created_at).total_seconds() / 3600
            holding_times.append(hours)
    stats.avg_holding_hours = round(np.mean(holding_times), 1) if holding_times else 0

    return stats


async def get_coin_stats(coin_symbol: str) -> SignalStats:
    """Get stats for a specific coin."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal).where(Signal.coin_symbol == coin_symbol).order_by(Signal.created_at)
        )
        signals = result.scalars().all()

    stats = SignalStats(period=f"All time — {coin_symbol}")
    if not signals:
        return stats

    stats.total = len(signals)
    stats.active = sum(1 for s in signals if s.status == SignalStatus.ACTIVE)
    closed_signals = [s for s in signals if s.status != SignalStatus.ACTIVE]
    pnl_values = []

    for s in closed_signals:
        pnl = s.pnl_percent or 0
        if s.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT):
            stats.wins += 1
        elif s.status == SignalStatus.STOPPED:
            stats.losses += 1
        elif s.status == SignalStatus.CLOSED:
            if pnl > 0:
                stats.partial_wins += 1
                stats.wins += 1
            else:
                stats.losses += 1
        elif s.status == SignalStatus.EXPIRED:
            stats.expired += 1
            if pnl > 0:
                stats.wins += 1
            elif pnl < 0:
                stats.losses += 1
        pnl_values.append(pnl)

    total_closed = stats.wins + stats.losses
    if total_closed > 0:
        stats.win_rate = round(stats.wins / total_closed * 100, 1)

    if pnl_values:
        winning_pnls = [p for p in pnl_values if p > 0]
        losing_pnls = [p for p in pnl_values if p < 0]
        stats.total_pnl = round(sum(pnl_values), 2)
        stats.best_trade = round(max(pnl_values), 2) if pnl_values else 0
        stats.worst_trade = round(min(pnl_values), 2) if pnl_values else 0
        stats.avg_win = round(np.mean(winning_pnls), 2) if winning_pnls else 0
        stats.avg_loss = round(np.mean(losing_pnls), 2) if losing_pnls else 0

    return stats
