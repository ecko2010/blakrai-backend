"""
Reports — aggregates stats data for daily/weekly digests and user-facing reports.
"""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from sqlalchemy import select, and_, func
from loguru import logger

from app.database import async_session
from app.models import Signal, SignalStatus, SignalDirection
from app.stats.calculator import compute_stats, SignalStats


@dataclass
class DigestData:
    period: str  # "daily" or "weekly"
    date_range: str
    stats: SignalStats | None = None
    top_signals: list = field(default_factory=list)
    worst_signals: list = field(default_factory=list)
    active_signals: list = field(default_factory=list)
    trending_coins: list = field(default_factory=list)
    summary_text: str = ""


async def generate_daily_digest() -> DigestData:
    """Generate data for the daily digest."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    stats = await compute_stats(start_date=start, end_date=now)

    digest = DigestData(
        period="daily",
        date_range=f"{start.strftime('%d.%m.%Y')} — {now.strftime('%d.%m.%Y')}",
        stats=stats,
    )

    async with async_session() as session:
        # Top performing signals (last 24h, sorted by PnL)
        top_result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.created_at >= start,
                    Signal.pnl_percent.isnot(None),
                    Signal.pnl_percent > 0,
                )
            ).order_by(Signal.pnl_percent.desc()).limit(5)
        )
        digest.top_signals = [
            {
                "coin": s.coin_symbol,
                "direction": s.direction.value,
                "pnl": round(s.pnl_percent, 2),
                "status": s.status.value,
                "entry": s.entry_price,
            }
            for s in top_result.scalars().all()
        ]

        # Worst signals
        worst_result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.created_at >= start,
                    Signal.pnl_percent.isnot(None),
                    Signal.pnl_percent < 0,
                )
            ).order_by(Signal.pnl_percent.asc()).limit(3)
        )
        digest.worst_signals = [
            {
                "coin": s.coin_symbol,
                "direction": s.direction.value,
                "pnl": round(s.pnl_percent, 2),
                "status": s.status.value,
            }
            for s in worst_result.scalars().all()
        ]

        # Currently active signals
        active_result = await session.execute(
            select(Signal).where(Signal.status == SignalStatus.ACTIVE).order_by(Signal.created_at.desc())
        )
        digest.active_signals = [
            {
                "coin": s.coin_symbol,
                "direction": s.direction.value,
                "entry": s.entry_price,
                "confidence": s.confidence_score,
            }
            for s in active_result.scalars().all()
        ]

        # Trending coins — most frequent in signals
        coin_counts = await session.execute(
            select(Signal.coin_symbol, func.count(Signal.id).label("cnt"))
            .where(Signal.created_at >= start)
            .group_by(Signal.coin_symbol)
            .order_by(func.count(Signal.id).desc())
            .limit(5)
        )
        digest.trending_coins = [
            {"coin": row[0], "signal_count": row[1]}
            for row in coin_counts.all()
        ]

    return digest


async def generate_weekly_digest() -> DigestData:
    """Generate data for the weekly digest."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    stats = await compute_stats(start_date=start, end_date=now)

    digest = DigestData(
        period="weekly",
        date_range=f"{start.strftime('%d.%m.%Y')} — {now.strftime('%d.%m.%Y')}",
        stats=stats,
    )

    async with async_session() as session:
        # Best trades of the week
        top_result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.created_at >= start,
                    Signal.pnl_percent.isnot(None),
                    Signal.pnl_percent > 0,
                )
            ).order_by(Signal.pnl_percent.desc()).limit(10)
        )
        digest.top_signals = [
            {
                "coin": s.coin_symbol,
                "direction": s.direction.value,
                "pnl": round(s.pnl_percent, 2),
                "status": s.status.value,
                "entry": s.entry_price,
                "exchange": s.exchange,
            }
            for s in top_result.scalars().all()
        ]

        # Worst trades of the week
        worst_result = await session.execute(
            select(Signal).where(
                and_(
                    Signal.created_at >= start,
                    Signal.pnl_percent.isnot(None),
                    Signal.pnl_percent < 0,
                )
            ).order_by(Signal.pnl_percent.asc()).limit(5)
        )
        digest.worst_signals = [
            {
                "coin": s.coin_symbol,
                "direction": s.direction.value,
                "pnl": round(s.pnl_percent, 2),
            }
            for s in worst_result.scalars().all()
        ]

        # Day-by-day PnL breakdown
        coin_counts = await session.execute(
            select(Signal.coin_symbol, func.count(Signal.id).label("cnt"))
            .where(Signal.created_at >= start)
            .group_by(Signal.coin_symbol)
            .order_by(func.count(Signal.id).desc())
            .limit(10)
        )
        digest.trending_coins = [
            {"coin": row[0], "signal_count": row[1]}
            for row in coin_counts.all()
        ]

    return digest


async def get_leaderboard(limit: int = 10) -> list[dict]:
    """Get top performing coins leaderboard."""
    async with async_session() as session:
        result = await session.execute(
            select(
                Signal.coin_symbol,
                func.count(Signal.id).label("total"),
                func.avg(Signal.pnl_percent).label("avg_pnl"),
                func.sum(Signal.pnl_percent).label("total_pnl"),
            )
            .where(Signal.pnl_percent.isnot(None))
            .group_by(Signal.coin_symbol)
            .having(func.count(Signal.id) >= 3)
            .order_by(func.avg(Signal.pnl_percent).desc())
            .limit(limit)
        )
        return [
            {
                "coin": row[0],
                "total_signals": row[1],
                "avg_pnl": round(float(row[2]), 2),
                "total_pnl": round(float(row[3]), 2),
            }
            for row in result.all()
        ]
