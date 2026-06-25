"""
Public API — no authentication required.
Delayed signals + aggregate stats for the marketing website.

ALL signal data is delayed by SIGNAL_DELAY_HOURS to protect paying subscribers.
Only closed/expired signals are shown. Active signals are NEVER exposed.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Query
from sqlalchemy import select, func, and_, desc, case, or_

from app.database import async_session
from app.models import Signal, SignalStatus, SignalDirection, User, Tier

router = APIRouter(prefix="/public", tags=["Public"])

# ── Delay: signals only visible after this many hours ──
SIGNAL_DELAY_HOURS = 4


# ─── Helpers ────────────────────────────────────────────

def _public_signal(s: Signal) -> dict:
    """Serialize a signal for public display — no sensitive data."""
    return {
        "id": s.id,
        "coin_symbol": s.coin_symbol,
        "direction": s.direction.value,
        "timeframe": s.timeframe,
        "exchange": s.exchange,
        "entry_price": s.entry_price,
        "stop_loss": s.stop_loss,
        "tp1": s.tp1,
        "tp2": s.tp2,
        "tp3": s.tp3,
        "confidence_score": s.confidence_score,
        "status": s.status.value,
        "pnl_percent": round(s.pnl_percent, 2) if s.pnl_percent is not None else None,
        "peak_profit_percent": round(s.peak_profit_percent, 2) if s.peak_profit_percent else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "closed_at": s.closed_at.isoformat() if s.closed_at else None,
    }


# ┌──────────────────────────────────────────────────────┐
# │ 1. STATS — aggregate performance for the website     │
# └──────────────────────────────────────────────────────┘

@router.get("/stats")
async def public_stats():
    """
    Aggregate trading statistics — win rate, total signals, PnL, etc.
    Safe to show on the marketing website. No user data exposed.
    """
    async with async_session() as session:
        total_signals = await session.scalar(select(func.count(Signal.id))) or 0
        active_signals = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
        ) or 0

        # Wins: TP hits + CLOSED with positive PnL
        tp_wins = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([
                    SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT
                ])
            )
        ) or 0
        partial_wins = await session.scalar(
            select(func.count(Signal.id)).where(
                and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent > 0)
            )
        ) or 0
        wins = tp_wins + partial_wins

        losses = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.STOPPED)
        ) or 0

        # PnL
        avg_pnl = await session.scalar(
            select(func.avg(Signal.pnl_percent)).where(Signal.pnl_percent.isnot(None))
        )
        total_pnl = await session.scalar(
            select(func.sum(Signal.pnl_percent)).where(Signal.pnl_percent.isnot(None))
        )
        best_trade = await session.scalar(
            select(func.max(Signal.pnl_percent)).where(Signal.pnl_percent.isnot(None))
        )

        # TP hit rates
        closed_count = wins + losses
        tp1_hits = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([
                    SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT
                ])
            )
        ) or 0
        tp2_hits = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([SignalStatus.TP2_HIT, SignalStatus.TP3_HIT])
            )
        ) or 0
        tp3_hits = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.TP3_HIT)
        ) or 0

        # 7-day stats
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        week_signals = await session.scalar(
            select(func.count(Signal.id)).where(Signal.created_at >= week_ago)
        ) or 0

        # User count (show social proof)
        total_users = await session.scalar(select(func.count(User.id))) or 0

    return {
        "total_signals": total_signals,
        "active_signals": active_signals,
        "this_week": week_signals,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / closed_count * 100, 1) if closed_count > 0 else 0,
        "avg_pnl_percent": round(avg_pnl or 0, 2),
        "total_pnl_percent": round(total_pnl or 0, 2),
        "best_trade_pnl": round(best_trade or 0, 2),
        "tp1_hit_rate": round(tp1_hits / closed_count * 100, 1) if closed_count > 0 else 0,
        "tp2_hit_rate": round(tp2_hits / closed_count * 100, 1) if closed_count > 0 else 0,
        "tp3_hit_rate": round(tp3_hits / closed_count * 100, 1) if closed_count > 0 else 0,
        "total_users": total_users,
    }


# ┌──────────────────────────────────────────────────────┐
# │ 2. SIGNALS — delayed closed signals for the website  │
# └──────────────────────────────────────────────────────┘

@router.get("/signals")
async def public_signals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    coin: str | None = Query(None, description="Filter by coin symbol"),
    direction: str | None = Query(None, description="long or short"),
    result: str | None = Query(None, description="win, loss, or all"),
):
    """
    Recent closed signals — delayed by 4 hours.
    Only shows signals that are already closed/expired (never active ones).
    Perfect for the website's "Recent Signals" / "Track Record" section.
    """
    delay_cutoff = datetime.now(timezone.utc) - timedelta(hours=SIGNAL_DELAY_HOURS)

    # Only final statuses — NEVER show active signals
    final_statuses = [
        SignalStatus.TP1_HIT,
        SignalStatus.TP2_HIT,
        SignalStatus.TP3_HIT,
        SignalStatus.STOPPED,
        SignalStatus.CLOSED,
        SignalStatus.EXPIRED,
    ]

    async with async_session() as session:
        query = (
            select(Signal)
            .where(
                and_(
                    Signal.status.in_(final_statuses),
                    Signal.created_at <= delay_cutoff,
                )
            )
            .order_by(desc(Signal.closed_at))
        )

        if coin:
            query = query.where(Signal.coin_symbol.ilike(f"%{coin}%"))
        if direction:
            try:
                query = query.where(Signal.direction == SignalDirection(direction))
            except ValueError:
                pass
        if result == "win":
            query = query.where(
                or_(
                    Signal.status.in_([
                        SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT
                    ]),
                    and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent > 0),
                )
            )
        elif result == "loss":
            query = query.where(Signal.status == SignalStatus.STOPPED)

        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0

        signals = (await session.execute(query.limit(limit).offset(offset))).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "delay_hours": SIGNAL_DELAY_HOURS,
        "items": [_public_signal(s) for s in signals],
    }


# ┌──────────────────────────────────────────────────────┐
# │ 3. TOP COINS — best performing coins                 │
# └──────────────────────────────────────────────────────┘

@router.get("/top-coins")
async def public_top_coins(limit: int = Query(10, ge=1, le=50)):
    """Top performing coins by win rate (min 3 closed signals)."""
    async with async_session() as session:
        result = await session.execute(
            select(
                Signal.coin_symbol,
                func.count(Signal.id).label("total"),
                func.sum(case(
                    (Signal.status.in_([
                        SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT
                    ]), 1),
                    (and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent > 0), 1),
                    else_=0,
                )).label("wins"),
                func.sum(case(
                    (Signal.status == SignalStatus.STOPPED, 1),
                    else_=0,
                )).label("losses"),
                func.avg(Signal.pnl_percent).label("avg_pnl"),
                func.max(Signal.pnl_percent).label("best_pnl"),
            )
            .where(Signal.pnl_percent.isnot(None))
            .group_by(Signal.coin_symbol)
            .having(func.count(Signal.id) >= 3)
            .order_by(desc(func.avg(Signal.pnl_percent)))
            .limit(limit)
        )
        rows = result.all()

    coins = []
    for row in rows:
        closed = (row.wins or 0) + (row.losses or 0)
        coins.append({
            "coin": row.coin_symbol,
            "total_signals": row.total,
            "wins": row.wins or 0,
            "losses": row.losses or 0,
            "win_rate": round((row.wins or 0) / closed * 100, 1) if closed > 0 else 0,
            "avg_pnl": round(row.avg_pnl or 0, 2),
            "best_pnl": round(row.best_pnl or 0, 2),
        })

    return {"coins": coins}


# ┌──────────────────────────────────────────────────────┐
# │ 4. STREAKS — current performance streaks             │
# └──────────────────────────────────────────────────────┘

@router.get("/streak")
async def public_streak():
    """Current win/loss streak and recent performance summary."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .where(Signal.pnl_percent.isnot(None))
            .order_by(desc(Signal.closed_at))
            .limit(20)
        )
        recent = result.scalars().all()

    if not recent:
        return {"current_streak": 0, "streak_type": "none", "last_10_wins": 0, "last_10_losses": 0}

    # Calculate streak
    streak = 0
    streak_type = ""
    for s in recent:
        pnl = s.pnl_percent or 0
        is_win = pnl > 0
        if streak == 0:
            streak_type = "win" if is_win else "loss"
            streak = 1
        elif (streak_type == "win" and is_win) or (streak_type == "loss" and not is_win):
            streak += 1
        else:
            break

    last_10 = recent[:10]
    last_10_wins = sum(1 for s in last_10 if (s.pnl_percent or 0) > 0)

    return {
        "current_streak": streak,
        "streak_type": streak_type,
        "last_10_wins": last_10_wins,
        "last_10_losses": len(last_10) - last_10_wins,
        "last_10_avg_pnl": round(
            sum((s.pnl_percent or 0) for s in last_10) / len(last_10), 2
        ) if last_10 else 0,
    }
