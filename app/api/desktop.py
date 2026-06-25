"""
Desktop App API — full-featured API for external desktop/mobile clients.

Auth: per-user API key via X-API-Key header (generated in Telegram bot).
Tier gating: FREE users see limited data; PRO/ELITE unlock full features.

Endpoints:
    GET  /desktop/me                — current user profile + tier info
    GET  /desktop/signals           — signals (active + recent closed)
    GET  /desktop/signals/{id}      — single signal detail with updates
    GET  /desktop/signals/active    — active signals only
    GET  /desktop/signals/activated — user's activated signals
    POST /desktop/signals/{id}/activate  — activate signal tracking
    DEL  /desktop/signals/{id}/activate  — deactivate signal tracking
    GET  /desktop/stats             — personal + global performance stats
    GET  /desktop/market            — real-time market overview (top coins)
    GET  /desktop/market/{coin}     — single coin detail with chart data
    GET  /desktop/news              — latest crypto news
    GET  /desktop/alerts            — user's alerts
    POST /desktop/alerts            — create alert
    DEL  /desktop/alerts/{id}       — delete alert
    GET  /desktop/watchlist         — user's watchlist
    POST /desktop/watchlist         — add coin to watchlist
    DEL  /desktop/watchlist/{coin}  — remove coin from watchlist
    GET  /desktop/wallets           — user's tracked wallets
    POST /desktop/wallets           — add wallet to track
    DEL  /desktop/wallets/{id}      — remove tracked wallet
    PATCH /desktop/wallets/{id}     — update wallet label
    PATCH /desktop/wallets/{id}/alerts   — update wallet alert config
    GET  /desktop/wallets/{id}/portfolio     — wallet token balances
    GET  /desktop/wallets/{id}/transactions  — wallet transactions (PRO+)
    GET  /desktop/wallets/{id}/analysis      — AI portfolio analysis (PRO+)
    WS   /desktop/ws                — real-time signal + price stream
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, desc, and_, case
from loguru import logger

from app.api.desktop_auth import require_desktop_auth, require_tier
from app.database import async_session
from app.models import (
    User, Signal, SignalUpdate, Subscription,
    UserAlert, UserWatchlist, NewsItem, MarketSnapshot,
    SignalStatus, SignalDirection, Tier, AlertType,
    UserSignalAction,
)

router = APIRouter(prefix="/desktop", tags=["Desktop App"])


# ─── Helpers ────────────────────────────────────────────

TIER_LEVEL = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}

# Signal fields visible per tier
def _serialize_signal(s: Signal, user_tier: Tier) -> dict:
    """Serialize signal with tier-based visibility."""
    user_level = TIER_LEVEL.get(user_tier, 0)
    signal_level = TIER_LEVEL.get(s.min_tier, 0)

    base = {
        "id": s.id,
        "coin_symbol": s.coin_symbol,
        "direction": s.direction.value,
        "status": s.status.value,
        "confidence": s.confidence_score,
        "exchange": s.exchange,
        "timeframe": s.timeframe,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "closed_at": s.closed_at.isoformat() if s.closed_at else None,
        "min_tier": s.min_tier.value,
    }

    # FREE users see coin + direction + confidence only for gated signals
    if user_level >= signal_level:
        base.update({
            "entry_price": s.entry_price,
            "entry_zone_low": s.entry_zone_low,
            "entry_zone_high": s.entry_zone_high,
            "stop_loss": s.stop_loss,
            "tp1": s.tp1,
            "tp2": s.tp2,
            "tp3": s.tp3,
            "leverage_suggested": s.leverage_suggested,
            "pnl_percent": s.pnl_percent,
            "peak_profit_percent": s.peak_profit_percent,
            "max_drawdown_percent": s.max_drawdown_percent,
            "ai_reasoning": s.ai_reasoning,
        })
    else:
        base.update({
            "entry_price": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "leverage_suggested": None,
            "locked": True,
            "upgrade_hint": f"Upgrade to {s.min_tier.value.upper()} to see full details",
        })

    # ELITE gets factors breakdown
    if user_tier == Tier.ELITE and user_level >= signal_level:
        base["factors"] = s.factors or {}
    
    return base


def _serialize_signal_update(u: SignalUpdate) -> dict:
    return {
        "id": u.id,
        "type": u.update_type.value,
        "price": u.price_at_update,
        "details": u.details,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


# ─── System Status ─────────────────────────────────────

@router.get("/status")
async def get_system_status(user: User = Depends(require_desktop_auth)):
    """System health — DB, Redis, scheduler, exchange connectivity, last scan time."""
    from app.redis_client import get_scan_heartbeat, redis_client as _rc

    last_scan = await get_scan_heartbeat()

    # DB
    db_ok = False
    try:
        from sqlalchemy import text
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # Scheduler
    scheduler_running = False
    scheduler_jobs = 0
    try:
        from app.scheduler import scheduler as _sched
        scheduler_running = _sched.running
        scheduler_jobs = len(_sched.get_jobs())
    except Exception:
        pass

    # Exchange health
    exchanges_status = {}
    try:
        from app.exchanges.manager import exchange_manager
        from app.exchanges.scoring import exchange_scorer
        for name in exchange_manager.exchanges:
            score = exchange_scorer.get_score(name)
            exchanges_status[name] = {
                "score": round(score.composite, 3),
                "success_rate": round(score.success_rate, 3),
                "latency_ms": round(score.latency_score * 1000, 0) if score.latency_score else None,
            }
    except Exception:
        pass

    # Active signals count
    active_signals = 0
    try:
        async with async_session() as session:
            active_signals = await session.scalar(
                select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
            ) or 0
    except Exception:
        pass

    return {
        "db_ok": db_ok,
        "redis_ok": _rc is not None,
        "scheduler_running": scheduler_running,
        "scheduler_jobs": scheduler_jobs,
        "last_scan": last_scan,
        "active_signals": active_signals,
        "exchanges": exchanges_status,
        "websocket_connections": ws_manager.connected_count if 'ws_manager' in globals() else 0,
    }


# ─── User Profile ──────────────────────────────────────

@router.get("/me")
async def get_profile(user: User = Depends(require_desktop_auth)):
    """Current user profile, subscription, and feature access."""
    # Get active subscription
    sub_info = None
    async with async_session() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
            ).order_by(desc(Subscription.expires_at)).limit(1)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub_info = {
                "tier": sub.tier.value,
                "expires_at": sub.expires_at.isoformat(),
                "auto_renew": sub.auto_renew,
            }

    features = _get_tier_features(user.tier)

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "language": user.language.value,
        "tier": user.tier.value,
        "subscription": sub_info,
        "features": features,
        "created_at": user.created_at.isoformat(),
    }


def _get_tier_features(tier: Tier) -> dict:
    """Feature availability per tier."""
    return {
        "signals_full_access": tier in (Tier.PRO, Tier.ELITE),
        "ai_reasoning": tier == Tier.ELITE,
        "alerts_limit": {Tier.FREE: 3, Tier.PRO: 20, Tier.ELITE: 100}.get(tier, 3),
        "watchlist_limit": {Tier.FREE: 5, Tier.PRO: 30, Tier.ELITE: 100}.get(tier, 5),
        "wallets_limit": {Tier.FREE: 1, Tier.PRO: 5, Tier.ELITE: 20}.get(tier, 1),
        "real_time_updates": tier in (Tier.PRO, Tier.ELITE),
        "market_data": True,
        "news_access": True,
        "signal_history": tier in (Tier.PRO, Tier.ELITE),
        "export_data": tier == Tier.ELITE,
        "wallet_tx_history": tier in (Tier.PRO, Tier.ELITE),
        "wallet_ai_analysis": tier in (Tier.PRO, Tier.ELITE),
    }


# ─── Signals ────────────────────────────────────────────

@router.get("/signals")
async def get_signals(
    user: User = Depends(require_desktop_auth),
    status: Optional[str] = Query(None, description="Filter: active, closed, all"),
    coin: Optional[str] = Query(None, description="Filter by coin symbol"),
    direction: Optional[str] = Query(None, description="Filter: long, short"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Paginated signals list. FREE users see limited details on PRO/ELITE signals."""
    offset = (page - 1) * limit

    async with async_session() as session:
        q = select(Signal)
        count_q = select(func.count(Signal.id))

        # Status filter
        if status == "active":
            q = q.where(Signal.status == SignalStatus.ACTIVE)
            count_q = count_q.where(Signal.status == SignalStatus.ACTIVE)
        elif status == "closed":
            closed_statuses = [
                SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED,
            ]
            q = q.where(Signal.status.in_(closed_statuses))
            count_q = count_q.where(Signal.status.in_(closed_statuses))

        if coin:
            q = q.where(Signal.coin_symbol == coin.upper())
            count_q = count_q.where(Signal.coin_symbol == coin.upper())
        if direction:
            d = SignalDirection.LONG if direction.lower() == "long" else SignalDirection.SHORT
            q = q.where(Signal.direction == d)
            count_q = count_q.where(Signal.direction == d)

        # FREE users only see recent 7 days of closed signals
        if user.tier == Tier.FREE and status != "active":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            q = q.where(Signal.created_at >= cutoff)
            count_q = count_q.where(Signal.created_at >= cutoff)

        total = await session.scalar(count_q)
        result = await session.execute(
            q.order_by(desc(Signal.created_at)).offset(offset).limit(limit)
        )
        signals = result.scalars().all()

    return {
        "signals": [_serialize_signal(s, user.tier) for s in signals],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.get("/signals/active")
async def get_active_signals(user: User = Depends(require_desktop_auth)):
    """All currently active signals — optimized for dashboard view."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .where(Signal.status == SignalStatus.ACTIVE)
            .order_by(desc(Signal.created_at))
        )
        signals = result.scalars().all()

    return {
        "signals": [_serialize_signal(s, user.tier) for s in signals],
        "count": len(signals),
    }


# ─── Signal Actions (Activated Signals) ────────────────

@router.get("/signals/activated")
async def get_activated_signals(
    user: User = Depends(require_desktop_auth),
    status: Optional[str] = Query(None, description="Filter: active, closed, all"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """User's activated signals (signals the user 'used'). Shows tracking status."""
    offset = (page - 1) * limit

    async with async_session() as session:
        q = (
            select(Signal, UserSignalAction.created_at.label("activated_at"))
            .join(UserSignalAction, UserSignalAction.signal_id == Signal.id)
            .where(UserSignalAction.user_id == user.id)
        )
        count_q = (
            select(func.count(UserSignalAction.id))
            .where(UserSignalAction.user_id == user.id)
        )

        if status == "active":
            active_statuses = [SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT]
            q = q.where(Signal.status.in_(active_statuses))
            count_q = count_q.join(Signal, Signal.id == UserSignalAction.signal_id).where(
                Signal.status.in_(active_statuses)
            )
        elif status == "closed":
            closed_statuses = [
                SignalStatus.TP3_HIT, SignalStatus.STOPPED,
                SignalStatus.CLOSED, SignalStatus.EXPIRED,
            ]
            q = q.where(Signal.status.in_(closed_statuses))
            count_q = count_q.join(Signal, Signal.id == UserSignalAction.signal_id).where(
                Signal.status.in_(closed_statuses)
            )

        total = await session.scalar(count_q) or 0
        result = await session.execute(
            q.order_by(desc(UserSignalAction.created_at)).offset(offset).limit(limit)
        )
        rows = result.all()

    signals = []
    for row in rows:
        signal = row[0]
        activated_at = row[1]
        data = _serialize_signal(signal, user.tier)
        data["activated_at"] = activated_at.isoformat() if activated_at else None
        signals.append(data)

    return {
        "signals": signals,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total else 0,
    }


@router.post("/signals/{signal_id}/activate", status_code=201)
async def activate_signal(
    signal_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Activate (use) a signal — marks it for tracking notifications."""
    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if not signal:
            raise HTTPException(404, "Signal not found")

        # Tier check
        user_level = TIER_LEVEL.get(user.tier, 0)
        signal_level = TIER_LEVEL.get(signal.min_tier, 0)
        if user_level < signal_level:
            raise HTTPException(403, f"Signal requires {signal.min_tier.value.upper()} tier")

        # Check duplicate
        existing = await session.scalar(
            select(UserSignalAction.id).where(
                UserSignalAction.user_id == user.id,
                UserSignalAction.signal_id == signal_id,
            )
        )
        if existing:
            raise HTTPException(409, "Signal already activated")

        action = UserSignalAction(
            user_id=user.id,
            signal_id=signal_id,
        )
        session.add(action)
        await session.commit()

    return {
        "status": "activated",
        "signal_id": signal_id,
        "signal": _serialize_signal(signal, user.tier),
    }


@router.delete("/signals/{signal_id}/activate")
async def deactivate_signal(
    signal_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Remove signal activation (stop tracking)."""
    async with async_session() as session:
        result = await session.execute(
            select(UserSignalAction).where(
                UserSignalAction.user_id == user.id,
                UserSignalAction.signal_id == signal_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(404, "Signal not activated")

        await session.delete(action)
        await session.commit()

    return {"status": "deactivated", "signal_id": signal_id}


@router.get("/signals/{signal_id}")
async def get_signal_detail(
    signal_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Single signal with full update history."""
    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if not signal:
            raise HTTPException(404, "Signal not found")

        # Get updates
        result = await session.execute(
            select(SignalUpdate)
            .where(SignalUpdate.signal_id == signal_id)
            .order_by(SignalUpdate.created_at)
        )
        updates = result.scalars().all()

    data = _serialize_signal(signal, user.tier)
    data["updates"] = [_serialize_signal_update(u) for u in updates]
    return data


# ─── Stats ──────────────────────────────────────────────

@router.get("/stats")
async def get_stats(user: User = Depends(require_desktop_auth)):
    """Global performance stats + user-specific data."""
    async with async_session() as session:
        # Global stats
        total = await session.scalar(select(func.count(Signal.id))) or 0
        active = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
        ) or 0

        # Wins = TP hits + any closed/stopped with positive PnL (partial wins / trailing SL)
        tp_wins = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT])
            )
        ) or 0
        partial_wins = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([SignalStatus.CLOSED, SignalStatus.STOPPED]),
                Signal.pnl_percent > 0,
            )
        ) or 0
        wins = tp_wins + partial_wins

        # Losses = STOPPED/CLOSED with pnl <= 0
        losses = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_([SignalStatus.STOPPED, SignalStatus.CLOSED]),
                Signal.pnl_percent <= 0,
            )
        ) or 0

        closed_total = wins + losses
        win_rate = round(wins / closed_total * 100, 1) if closed_total > 0 else 0

        # PnL for all closed signals (TP hits + STOPPED + CLOSED)
        closed_statuses = [
            SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
            SignalStatus.STOPPED, SignalStatus.CLOSED,
        ]
        avg_pnl = await session.scalar(
            select(func.avg(Signal.pnl_percent)).where(
                Signal.pnl_percent.isnot(None),
                Signal.status.in_(closed_statuses),
            )
        ) or 0

        total_pnl = await session.scalar(
            select(func.sum(Signal.pnl_percent)).where(
                Signal.pnl_percent.isnot(None),
                Signal.status.in_(closed_statuses),
            )
        ) or 0

        # Last 30 days for chart
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        monthly_signals = await session.scalar(
            select(func.count(Signal.id)).where(Signal.created_at >= month_ago)
        ) or 0

        # User-specific: alerts, watchlist counts, activated signals
        user_alerts_count = await session.scalar(
            select(func.count(UserAlert.id)).where(
                UserAlert.user_id == user.id, UserAlert.is_active == True
            )
        ) or 0
        user_watchlist_count = await session.scalar(
            select(func.count(UserWatchlist.id)).where(UserWatchlist.user_id == user.id)
        ) or 0
        user_activated = await session.scalar(
            select(func.count(UserSignalAction.id)).where(
                UserSignalAction.user_id == user.id,
            )
        ) or 0
        # User's wallets count
        user_wallets_count = await session.scalar(
            select(func.count(TrackedWallet.id)).where(
                TrackedWallet.user_id == user.id,
                TrackedWallet.is_active == True,
            )
        ) or 0

    return {
        "global": {
            "total_signals": total,
            "active_signals": active,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "average_pnl": round(float(avg_pnl), 2),
            "total_pnl": round(float(total_pnl), 2),
            "signals_last_30d": monthly_signals,
        },
        "user": {
            "tier": user.tier.value,
            "alerts_active": user_alerts_count,
            "watchlist_size": user_watchlist_count,
            "signals_activated": user_activated,
            "wallets_count": user_wallets_count,
        },
    }


# ─── Market Data ────────────────────────────────────────

@router.get("/market")
async def get_market_overview(
    user: User = Depends(require_desktop_auth),
    limit: int = Query(50, ge=1, le=200),
):
    """Top coins by recent snapshot data — latest prices from all exchanges."""
    from app.models import CoinMeta

    async with async_session() as session:
        # Get latest snapshot per coin (most recent only)
        subq = (
            select(
                MarketSnapshot.coin_symbol,
                func.max(MarketSnapshot.id).label("max_id"),
            )
            .group_by(MarketSnapshot.coin_symbol)
            .subquery()
        )
        result = await session.execute(
            select(MarketSnapshot)
            .join(subq, MarketSnapshot.id == subq.c.max_id)
            .order_by(desc(MarketSnapshot.volume_24h))
            .limit(limit)
        )
        snapshots = result.scalars().all()

        # Bulk-fetch coin metadata for logos
        coin_symbols = [s.coin_symbol for s in snapshots]
        meta_result = await session.execute(
            select(CoinMeta).where(CoinMeta.symbol.in_(coin_symbols))
        )
        meta_map = {m.symbol: m for m in meta_result.scalars().all()}

    coins = []
    for s in snapshots:
        meta = meta_map.get(s.coin_symbol)
        coins.append({
            "coin": s.coin_symbol,
            "name": meta.name if meta else None,
            "logo_url": meta.logo_url if meta else None,
            "price": s.price,
            "volume_24h": s.volume_24h,
            "change_1h": s.price_change_1h,
            "change_24h": s.price_change_24h,
            "change_7d": s.price_change_7d,
            "market_cap": meta.market_cap if meta else None,
            "market_cap_rank": meta.market_cap_rank if meta else None,
            "exchange": s.exchange,
            "updated_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {"coins": coins, "count": len(coins)}


@router.get("/market/{coin}")
async def get_coin_detail(
    coin: str,
    user: User = Depends(require_desktop_auth),
    hours: int = Query(24, ge=1, le=168, description="Hours of price history"),
):
    """Single coin with multi-exchange prices and history."""
    from app.models import CoinMeta

    coin = coin.upper()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with async_session() as session:
        # Coin metadata (logo, name, etc.)
        meta = await session.scalar(
            select(CoinMeta).where(CoinMeta.symbol == coin)
        )

        # Current prices across exchanges
        subq = (
            select(
                MarketSnapshot.exchange,
                func.max(MarketSnapshot.id).label("max_id"),
            )
            .where(MarketSnapshot.coin_symbol == coin)
            .group_by(MarketSnapshot.exchange)
            .subquery()
        )
        result = await session.execute(
            select(MarketSnapshot)
            .join(subq, MarketSnapshot.id == subq.c.max_id)
        )
        current = result.scalars().all()

        if not current:
            raise HTTPException(404, f"No data for {coin}")

        # Price history (limited to prevent unbounded fetch)
        result = await session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.coin_symbol == coin, MarketSnapshot.created_at >= cutoff)
            .order_by(MarketSnapshot.created_at)
            .limit(2000)
        )
        history = result.scalars().all()

        # Active signals for this coin
        result = await session.execute(
            select(Signal).where(
                Signal.coin_symbol == coin,
                Signal.status == SignalStatus.ACTIVE,
            )
        )
        active_signals = result.scalars().all()

    return {
        "coin": coin,
        "name": meta.name if meta else None,
        "logo_url": meta.logo_url if meta else None,
        "market_cap": meta.market_cap if meta else None,
        "market_cap_rank": meta.market_cap_rank if meta else None,
        "circulating_supply": meta.circulating_supply if meta else None,
        "ath": meta.ath if meta else None,
        "atl": meta.atl if meta else None,
        "exchanges": [
            {
                "exchange": s.exchange,
                "price": s.price,
                "volume_24h": s.volume_24h,
                "change_24h": s.price_change_24h,
                "extra": s.extra_data,
            }
            for s in current
        ],
        "price_history": [
            {
                "price": s.price,
                "exchange": s.exchange,
                "timestamp": s.created_at.isoformat(),
            }
            for s in history
        ],
        "active_signals": [_serialize_signal(s, user.tier) for s in active_signals],
    }


# ─── Historical Candles ─────────────────────────────────

@router.get("/candles/{coin}")
async def get_candles(
    coin: str,
    user: User = Depends(require_desktop_auth),
    exchange: Optional[str] = Query(None, description="Filter by exchange (e.g. binance)"),
    timeframe: str = Query("1h", regex="^(15m|1h|4h|1d)$", description="Candle timeframe"),
    limit: int = Query(200, ge=1, le=1000),
    from_ts: Optional[str] = Query(None, description="ISO start date"),
    to_ts: Optional[str] = Query(None, description="ISO end date"),
):
    """Historical OHLCV candles for a coin. FREE: 1h/4h only, last 24h. PRO: all tf, 7d. ELITE: full history."""
    from app.models import CandleRecord, CandleTimeframe, CoinMeta

    coin = coin.upper()
    tier_level = {"free": 0, "pro": 1, "elite": 2}.get(user.tier.value, 0)

    # Tier restrictions
    allowed_tf = {"15m", "1h", "4h", "1d"}
    if tier_level == 0:
        allowed_tf = {"1h", "4h"}
        max_hours_back = 24
    elif tier_level == 1:
        max_hours_back = 168  # 7 days
    else:
        max_hours_back = None  # unlimited

    if timeframe not in allowed_tf:
        raise HTTPException(403, f"Timeframe {timeframe} not available for your tier")

    tf_enum = CandleTimeframe(timeframe)

    # Build query
    conditions = [
        CandleRecord.coin_symbol == coin,
        CandleRecord.timeframe == tf_enum,
    ]

    if exchange:
        conditions.append(CandleRecord.exchange == exchange.lower())

    if from_ts:
        try:
            conditions.append(CandleRecord.open_time >= datetime.fromisoformat(from_ts))
        except ValueError:
            raise HTTPException(400, "Invalid from_ts format")

    if to_ts:
        try:
            conditions.append(CandleRecord.open_time <= datetime.fromisoformat(to_ts))
        except ValueError:
            raise HTTPException(400, "Invalid to_ts format")

    if max_hours_back and not from_ts:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours_back)
        conditions.append(CandleRecord.open_time >= cutoff)

    async with async_session() as session:
        result = await session.execute(
            select(CandleRecord)
            .where(and_(*conditions))
            .order_by(desc(CandleRecord.open_time))
            .limit(limit)
        )
        candles = result.scalars().all()

    return {
        "coin": coin,
        "timeframe": timeframe,
        "exchange": exchange,
        "count": len(candles),
        "candles": [
            {
                "t": c.open_time.isoformat(),
                "o": c.open,
                "h": c.high,
                "l": c.low,
                "c": c.close,
                "v": c.volume,
                "ex": c.exchange,
            }
            for c in reversed(candles)  # oldest first for charting
        ],
    }


@router.get("/candles/{coin}/exchanges")
async def get_candle_exchanges(
    coin: str,
    user: User = Depends(require_desktop_auth),
):
    """List available exchanges and timeframes for a coin's historical data."""
    from app.models import CandleRecord

    coin = coin.upper()
    async with async_session() as session:
        result = await session.execute(
            select(
                CandleRecord.exchange,
                CandleRecord.timeframe,
                func.count(CandleRecord.id).label("count"),
                func.min(CandleRecord.open_time).label("earliest"),
                func.max(CandleRecord.open_time).label("latest"),
            )
            .where(CandleRecord.coin_symbol == coin)
            .group_by(CandleRecord.exchange, CandleRecord.timeframe)
        )
        rows = result.all()

    if not rows:
        raise HTTPException(404, f"No candle data for {coin}")

    exchanges = {}
    for row in rows:
        ex_name = row.exchange
        if ex_name not in exchanges:
            exchanges[ex_name] = {"exchange": ex_name, "timeframes": []}
        exchanges[ex_name]["timeframes"].append({
            "tf": row.timeframe.value if hasattr(row.timeframe, 'value') else row.timeframe,
            "count": row.count,
            "from": row.earliest.isoformat() if row.earliest else None,
            "to": row.latest.isoformat() if row.latest else None,
        })

    return {"coin": coin, "exchanges": list(exchanges.values())}


# ─── Coin Metadata ──────────────────────────────────────

@router.get("/coins")
async def get_coin_list(
    user: User = Depends(require_desktop_auth),
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List coins with metadata (logo, market cap, supply, etc.)."""
    from app.models import CoinMeta

    async with async_session() as session:
        query = select(CoinMeta)

        if search:
            search_upper = f"%{search.upper()}%"
            search_lower = f"%{search.lower()}%"
            query = query.where(
                (CoinMeta.symbol.ilike(search_upper)) |
                (CoinMeta.name.ilike(search_lower))
            )

        query = query.order_by(CoinMeta.market_cap_rank.asc().nullslast()).offset(offset).limit(limit)
        result = await session.execute(query)
        coins = result.scalars().all()

    return {
        "count": len(coins),
        "coins": [_serialize_coin_meta(c, user.tier) for c in coins],
    }


@router.get("/coins/{symbol}")
async def get_coin_detail_meta(
    symbol: str,
    user: User = Depends(require_desktop_auth),
):
    """Detailed coin metadata with logo, supply, ATH/ATL, exchanges."""
    from app.models import CoinMeta

    symbol = symbol.upper()
    async with async_session() as session:
        result = await session.execute(
            select(CoinMeta).where(CoinMeta.symbol == symbol)
        )
        coin = result.scalar_one_or_none()

    if not coin:
        raise HTTPException(404, f"No metadata for {symbol}")

    return _serialize_coin_meta(coin, user.tier)


def _serialize_coin_meta(c, user_tier) -> dict:
    """Serialize CoinMeta with tier visibility."""
    tier_level = {"free": 0, "pro": 1, "elite": 2}.get(user_tier.value, 0)

    base = {
        "symbol": c.symbol,
        "name": c.name,
        "logo_url": c.logo_url,
        "logo_thumb_url": c.logo_thumb_url,
        "market_cap": c.market_cap,
        "market_cap_rank": c.market_cap_rank,
        "exchanges_available": c.exchanges_available,
    }

    if tier_level >= 1:
        base.update({
            "circulating_supply": c.circulating_supply,
            "total_supply": c.total_supply,
            "max_supply": c.max_supply,
            "ath": c.ath,
            "ath_date": c.ath_date.isoformat() if c.ath_date else None,
            "atl": c.atl,
            "atl_date": c.atl_date.isoformat() if c.atl_date else None,
        })

    if tier_level >= 2:
        base.update({
            "coingecko_id": c.coingecko_id,
            "categories": c.categories,
            "description_en": c.description_en,
            "homepage_url": c.homepage_url,
        })

    return base


# ─── AI Analysis ────────────────────────────────────────

@router.get("/analysis")
async def get_ai_analysis(
    user: User = Depends(require_desktop_auth),
    analysis_type: Optional[str] = Query(None, description="market_overview, coin_analysis, trend_report"),
    coin: Optional[str] = Query(None, description="Filter by coin symbol"),
    days: int = Query(7, ge=1, le=90),
):
    """AI-generated market analysis. FREE: latest overview only. PRO: 7d. ELITE: 90d + all types."""
    from app.models import DailyAIAnalysis

    tier_level = {"free": 0, "pro": 1, "elite": 2}.get(user.tier.value, 0)

    # Tier restrictions
    if tier_level == 0:
        days = 1
        analysis_type = "market_overview"
    elif tier_level == 1:
        days = min(days, 7)

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)

    conditions = [DailyAIAnalysis.date >= cutoff]
    if analysis_type:
        conditions.append(DailyAIAnalysis.analysis_type == analysis_type)
    if coin:
        conditions.append(DailyAIAnalysis.coin_symbol == coin.upper())

    async with async_session() as session:
        result = await session.execute(
            select(DailyAIAnalysis)
            .where(and_(*conditions))
            .order_by(desc(DailyAIAnalysis.date), DailyAIAnalysis.analysis_type)
            .limit(100)
        )
        analyses = result.scalars().all()

    return {
        "count": len(analyses),
        "analyses": [
            {
                "id": a.id,
                "date": a.date.isoformat() if hasattr(a.date, 'isoformat') else str(a.date),
                "coin": a.coin_symbol,
                "type": a.analysis_type,
                "content": a.content,
                "metrics": a.metrics if tier_level >= 1 else None,
            }
            for a in analyses
        ],
    }


@router.get("/analysis/latest")
async def get_latest_analysis(
    user: User = Depends(require_desktop_auth),
):
    """Get the latest daily analysis (overview + trend report)."""
    from app.models import DailyAIAnalysis

    async with async_session() as session:
        # Get the most recent date that has analyses
        latest_date = await session.scalar(
            select(func.max(DailyAIAnalysis.date))
        )
        if not latest_date:
            return {"date": None, "overview": None, "trend_report": None, "coin_analyses": []}

        result = await session.execute(
            select(DailyAIAnalysis).where(DailyAIAnalysis.date == latest_date)
        )
        analyses = result.scalars().all()

    tier_level = {"free": 0, "pro": 1, "elite": 2}.get(user.tier.value, 0)
    overview = None
    trend_report = None
    coin_analyses = []

    for a in analyses:
        entry = {
            "coin": a.coin_symbol,
            "type": a.analysis_type,
            "content": a.content,
            "metrics": a.metrics if tier_level >= 1 else None,
        }
        if a.analysis_type == "market_overview":
            overview = entry
        elif a.analysis_type == "trend_report":
            trend_report = entry
        elif a.analysis_type == "coin_analysis":
            coin_analyses.append(entry)

    # FREE tier only sees overview
    if tier_level == 0:
        coin_analyses = coin_analyses[:3]
        trend_report = None

    return {
        "date": latest_date.isoformat() if hasattr(latest_date, 'isoformat') else str(latest_date),
        "overview": overview,
        "trend_report": trend_report,
        "coin_analyses": coin_analyses,
    }


# ─── News ───────────────────────────────────────────────

@router.get("/news")
async def get_news(
    user: User = Depends(require_desktop_auth),
    coin: Optional[str] = Query(None, description="Filter by mentioned coin"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Latest crypto news. FREE: last 24h only. PRO/ELITE: full history."""
    offset = (page - 1) * limit

    async with async_session() as session:
        q = select(NewsItem)
        count_q = select(func.count(NewsItem.id))

        # FREE: 24h only
        if user.tier == Tier.FREE:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            q = q.where(NewsItem.created_at >= cutoff)
            count_q = count_q.where(NewsItem.created_at >= cutoff)

        if coin:
            # Filter by coins_mentioned JSON array containing the coin
            q = q.where(NewsItem.coins_mentioned.contains([coin.upper()]))
            count_q = count_q.where(NewsItem.coins_mentioned.contains([coin.upper()]))

        total = await session.scalar(count_q) or 0
        result = await session.execute(
            q.order_by(desc(NewsItem.created_at)).offset(offset).limit(limit)
        )
        items = result.scalars().all()

    return {
        "news": [
            {
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
                "source": n.source,
                "url": n.url,
                "sentiment": n.sentiment,
                "importance": n.importance_score,
                "coins": n.coins_mentioned,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total else 0,
    }


# ─── Alerts ─────────────────────────────────────────────

@router.get("/alerts")
async def get_alerts(user: User = Depends(require_desktop_auth)):
    """List user's active alerts."""
    async with async_session() as session:
        result = await session.execute(
            select(UserAlert)
            .where(UserAlert.user_id == user.id)
            .order_by(desc(UserAlert.created_at))
        )
        alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": a.id,
                "coin": a.coin_symbol,
                "type": a.alert_type.value,
                "params": a.params,
                "is_active": a.is_active,
                "triggered_count": a.triggered_count,
                "last_triggered": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
                "cooldown_minutes": a.cooldown_minutes,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "count": len(alerts),
        "limit": _get_tier_features(user.tier)["alerts_limit"],
    }


@router.post("/alerts", status_code=201)
async def create_alert(
    coin: str = Query(..., description="Coin symbol (e.g. BTC)"),
    alert_type: str = Query(..., description="Alert type"),
    params: Optional[str] = Query(None, description="JSON params"),
    cooldown: int = Query(60, ge=5, le=1440, description="Cooldown in minutes"),
    user: User = Depends(require_desktop_auth),
):
    """Create a new alert. Respects tier limits."""
    import json as _json

    # Validate alert type
    try:
        at = AlertType(alert_type)
    except ValueError:
        raise HTTPException(400, f"Invalid alert_type. Valid: {[a.value for a in AlertType]}")

    # Check limit
    features = _get_tier_features(user.tier)
    async with async_session() as session:
        current_count = await session.scalar(
            select(func.count(UserAlert.id)).where(
                UserAlert.user_id == user.id, UserAlert.is_active == True
            )
        ) or 0

        if current_count >= features["alerts_limit"]:
            raise HTTPException(
                403,
                f"Alert limit reached ({features['alerts_limit']}). "
                f"Upgrade your tier for more alerts.",
            )

        parsed_params = {}
        if params:
            try:
                parsed_params = _json.loads(params)
            except _json.JSONDecodeError:
                raise HTTPException(400, "Invalid JSON in params")

        alert = UserAlert(
            user_id=user.id,
            coin_symbol=coin.upper(),
            alert_type=at,
            params=parsed_params,
            cooldown_minutes=cooldown,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

    return {
        "id": alert.id,
        "coin": alert.coin_symbol,
        "type": alert.alert_type.value,
        "params": alert.params,
        "cooldown_minutes": alert.cooldown_minutes,
        "created_at": alert.created_at.isoformat(),
    }


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Deactivate an alert."""
    async with async_session() as session:
        alert = await session.get(UserAlert, alert_id)
        if not alert or alert.user_id != user.id:
            raise HTTPException(404, "Alert not found")

        alert.is_active = False
        session.add(alert)
        await session.commit()

    return {"status": "deleted", "id": alert_id}


# ─── Watchlist ──────────────────────────────────────────

@router.get("/watchlist")
async def get_watchlist(user: User = Depends(require_desktop_auth)):
    """User's watched coins with latest prices."""
    async with async_session() as session:
        result = await session.execute(
            select(UserWatchlist)
            .where(UserWatchlist.user_id == user.id)
            .order_by(UserWatchlist.added_at)
        )
        items = result.scalars().all()

        # Get latest prices for all watched coins in one query
        prices = {}
        coin_symbols = [item.coin_symbol for item in items]
        if coin_symbols:
            from sqlalchemy import and_
            # Subquery: max snapshot id per coin
            max_ids_subq = (
                select(
                    MarketSnapshot.coin_symbol,
                    func.max(MarketSnapshot.id).label("max_id")
                )
                .where(MarketSnapshot.coin_symbol.in_(coin_symbols))
                .group_by(MarketSnapshot.coin_symbol)
                .subquery()
            )
            snap_result = await session.execute(
                select(MarketSnapshot).join(
                    max_ids_subq,
                    and_(
                        MarketSnapshot.id == max_ids_subq.c.max_id,
                        MarketSnapshot.coin_symbol == max_ids_subq.c.coin_symbol,
                    )
                )
            )
            for snap in snap_result.scalars().all():
                prices[snap.coin_symbol] = {
                    "price": snap.price,
                    "change_24h": snap.price_change_24h,
                    "volume_24h": snap.volume_24h,
                }

    return {
        "watchlist": [
            {
                "coin": w.coin_symbol,
                "added_at": w.added_at.isoformat(),
                "market": prices.get(w.coin_symbol),
            }
            for w in items
        ],
        "count": len(items),
        "limit": _get_tier_features(user.tier)["watchlist_limit"],
    }


@router.post("/watchlist", status_code=201)
async def add_to_watchlist(
    coin: str = Query(..., description="Coin symbol (e.g. BTC)"),
    user: User = Depends(require_desktop_auth),
):
    """Add a coin to watchlist. Respects tier limits."""
    coin = coin.upper()
    features = _get_tier_features(user.tier)

    async with async_session() as session:
        count = await session.scalar(
            select(func.count(UserWatchlist.id)).where(UserWatchlist.user_id == user.id)
        ) or 0

        if count >= features["watchlist_limit"]:
            raise HTTPException(
                403,
                f"Watchlist limit reached ({features['watchlist_limit']}). Upgrade tier for more.",
            )

        # Check duplicate
        existing = await session.execute(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.coin_symbol == coin,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, f"{coin} already in watchlist")

        item = UserWatchlist(user_id=user.id, coin_symbol=coin)
        session.add(item)
        await session.commit()
        await session.refresh(item)

    return {"coin": coin, "added_at": item.added_at.isoformat()}


@router.delete("/watchlist/{coin}")
async def remove_from_watchlist(
    coin: str,
    user: User = Depends(require_desktop_auth),
):
    """Remove coin from watchlist."""
    coin = coin.upper()

    async with async_session() as session:
        result = await session.execute(
            select(UserWatchlist).where(
                UserWatchlist.user_id == user.id,
                UserWatchlist.coin_symbol == coin,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(404, f"{coin} not in watchlist")

        await session.delete(item)
        await session.commit()

    return {"status": "removed", "coin": coin}


# ─── Wallet Tracker ────────────────────────────────────

from app.models import TrackedWallet, WalletToken, WalletTransaction, ChainType


@router.get("/wallets")
async def get_wallets(user: User = Depends(require_desktop_auth)):
    """Get all tracked wallets for the user."""
    from app.wallet.tracker import wallet_tracker, WALLET_LIMITS
    wallets = await wallet_tracker.get_user_wallets(user.id)
    limit = WALLET_LIMITS.get(user.tier, 1)

    return {
        "wallets": [
            {
                "id": w.id,
                "address": w.address,
                "chain": w.chain.value,
                "label": w.label,
                "total_value_usd": w.total_value_usd,
                "native_balance": w.native_balance,
                "last_scanned_at": w.last_scanned_at.isoformat() if w.last_scanned_at else None,
                "tokens_count": len(w.tokens) if w.tokens else 0,
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in wallets
        ],
        "limit": limit,
        "count": len(wallets),
    }


@router.post("/wallets")
async def add_wallet(
    address: str,
    chain: str | None = None,
    label: str | None = None,
    user: User = Depends(require_desktop_auth),
):
    """Add a new wallet to track."""
    from app.wallet.tracker import wallet_tracker

    chain_enum = None
    if chain:
        try:
            chain_enum = ChainType(chain.lower())
        except ValueError:
            raise HTTPException(400, f"Unsupported chain: {chain}")

    result = await wallet_tracker.add_wallet(user.id, address, chain_enum, label)

    if isinstance(result, str):
        error_map = {
            "unknown_chain": (400, "Could not detect chain from address"),
            "user_not_found": (404, "User not found"),
            "limit_reached": (403, "Wallet limit reached for your tier"),
            "already_tracked": (409, "Wallet already tracked"),
        }
        status, msg = error_map.get(result, (400, result))
        raise HTTPException(status, msg)

    return {
        "id": result.id,
        "address": result.address,
        "chain": result.chain.value,
        "label": result.label,
        "status": "added",
    }


@router.delete("/wallets/{wallet_id}")
async def remove_wallet(
    wallet_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Remove a tracked wallet."""
    from app.wallet.tracker import wallet_tracker
    success = await wallet_tracker.remove_wallet(user.id, wallet_id)
    if not success:
        raise HTTPException(404, "Wallet not found")
    return {"status": "removed", "wallet_id": wallet_id}


@router.get("/wallets/{wallet_id}/portfolio")
async def get_wallet_portfolio(
    wallet_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Get portfolio (token balances) for a wallet."""
    from app.wallet.tracker import wallet_tracker
    portfolio = await wallet_tracker.get_wallet_portfolio(wallet_id)

    if not portfolio:
        raise HTTPException(404, "Wallet not found")

    wallet = portfolio["wallet"]
    if wallet.user_id != user.id:
        raise HTTPException(404, "Wallet not found")

    tokens = portfolio["tokens"]

    return {
        "wallet_id": wallet_id,
        "address": wallet.address,
        "chain": wallet.chain.value,
        "label": wallet.label,
        "total_value_usd": portfolio["total_value_usd"],
        "last_scanned": wallet.last_scanned_at.isoformat() if wallet.last_scanned_at else None,
        "tokens": [
            {
                "symbol": t.symbol,
                "name": t.name,
                "contract_address": t.contract_address,
                "balance": t.balance,
                "price_usd": t.price_usd,
                "value_usd": t.value_usd,
                "logo_url": t.logo_url,
                "decimals": t.decimals,
            }
            for t in tokens
        ],
    }


@router.get("/wallets/{wallet_id}/transactions")
async def get_wallet_transactions(
    wallet_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_desktop_auth),
):
    """Get transactions for a wallet. Requires PRO+."""
    from app.wallet.tracker import wallet_tracker, TIER_FEATURES
    if "tx_alerts" not in TIER_FEATURES.get(user.tier, set()):
        raise HTTPException(403, "Transaction history requires PRO subscription")

    # Verify ownership
    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != user.id:
            raise HTTPException(404, "Wallet not found")

    txs = await wallet_tracker.get_wallet_transactions(wallet_id, limit=limit, offset=offset)

    return {
        "wallet_id": wallet_id,
        "transactions": [
            {
                "tx_hash": tx.tx_hash,
                "chain": tx.chain.value,
                "block_number": tx.block_number,
                "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "tx_type": tx.tx_type,
                "token_symbol": tx.token_symbol,
                "amount": tx.amount,
                "amount_usd": tx.amount_usd,
                "token_out_symbol": tx.token_out_symbol,
                "amount_out": tx.amount_out,
                "fee": tx.fee,
                "fee_usd": tx.fee_usd,
            }
            for tx in txs
        ],
        "count": len(txs),
    }


@router.get("/wallets/{wallet_id}/analysis")
async def get_wallet_analysis(
    wallet_id: int,
    user: User = Depends(require_desktop_auth),
):
    """Get AI portfolio analysis. Requires PRO+."""
    from app.wallet.tracker import TIER_FEATURES
    if "analytics" not in TIER_FEATURES.get(user.tier, set()):
        raise HTTPException(403, "AI analytics requires PRO subscription")

    # Verify ownership
    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != user.id:
            raise HTTPException(404, "Wallet not found")

    from app.wallet.analytics import generate_portfolio_analysis
    analysis = await generate_portfolio_analysis(wallet_id)

    if not analysis:
        raise HTTPException(500, "Analysis generation failed")

    return {
        "wallet_id": wallet_id,
        "analysis": analysis,
    }


@router.patch("/wallets/{wallet_id}/alerts")
async def update_wallet_alert_config(
    wallet_id: int,
    new_tx: Optional[bool] = Query(None, description="Alert on new transactions"),
    new_token: Optional[bool] = Query(None, description="Alert on new tokens"),
    large_transfer_usd: Optional[float] = Query(None, ge=0, description="Large transfer threshold in USD"),
    user: User = Depends(require_desktop_auth),
):
    """Update wallet alert configuration."""
    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != user.id:
            raise HTTPException(404, "Wallet not found")

        config = wallet.alert_config or {}
        if new_tx is not None:
            config["new_tx"] = new_tx
        if new_token is not None:
            config["new_token"] = new_token
        if large_transfer_usd is not None:
            config["large_transfer_usd"] = large_transfer_usd

        wallet.alert_config = config
        session.add(wallet)
        await session.commit()

    return {
        "wallet_id": wallet_id,
        "alert_config": config,
    }


@router.patch("/wallets/{wallet_id}")
async def update_wallet(
    wallet_id: int,
    label: Optional[str] = Query(None, description="New label for wallet"),
    user: User = Depends(require_desktop_auth),
):
    """Update wallet label."""
    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != user.id:
            raise HTTPException(404, "Wallet not found")

        if label is not None:
            wallet.label = label[:100]
        session.add(wallet)
        await session.commit()

    return {
        "wallet_id": wallet_id,
        "label": wallet.label,
        "status": "updated",
    }


# ─── WebSocket — Real-time stream ──────────────────────

import hashlib
import json as _json
from app.models import UserApiKey


class ConnectionManager:
    """Manages active WebSocket connections per user."""
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}  # user_id -> connections
        self._user_tiers: dict[int, Tier] = {}  # user_id -> tier
        self._subscribed_coins: dict[int, set[str]] = {}  # user_id -> coins

    async def connect(self, ws: WebSocket, user_id: int, tier: Tier):
        await ws.accept()
        if user_id not in self.active:
            self.active[user_id] = []
        self.active[user_id].append(ws)
        self._user_tiers[user_id] = tier
        logger.info(f"WS connected: user {user_id} ({len(self.active[user_id])} connections)")

    def disconnect(self, ws: WebSocket, user_id: int):
        if user_id in self.active:
            self.active[user_id] = [c for c in self.active[user_id] if c is not ws]
            if not self.active[user_id]:
                del self.active[user_id]
                self._user_tiers.pop(user_id, None)
                self._subscribed_coins.pop(user_id, None)
        logger.info(f"WS disconnected: user {user_id}")

    def set_subscribed_coins(self, user_id: int, coins: set[str]):
        self._subscribed_coins[user_id] = coins

    async def send_to_user(self, user_id: int, data: dict):
        if user_id in self.active:
            dead = []
            for ws in self.active[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active[user_id].remove(ws)

    async def broadcast(self, data: dict, min_tier: Tier = Tier.FREE):
        """Broadcast to all connected users, filtered by tier and coin subscriptions."""
        tier_level = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
        required_level = tier_level.get(min_tier, 0)
        coin = data.get("signal", {}).get("coin") or data.get("coin")

        for user_id, connections in list(self.active.items()):
            # Tier check
            user_tier = self._user_tiers.get(user_id, Tier.FREE)
            if tier_level.get(user_tier, 0) < required_level:
                continue

            # Coin subscription filter (if user subscribed to specific coins)
            user_coins = self._subscribed_coins.get(user_id)
            if user_coins and coin and coin not in user_coins:
                continue

            for ws in connections:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

    @property
    def connected_count(self) -> int:
        return sum(len(conns) for conns in self.active.values())


ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time WebSocket stream.

    Auth: send {"type": "auth", "key": "brk_..."} as first message.

    Receives:
        - signal_new: new signal generated
        - signal_update: signal updated (TP hit, SL, etc.)
        - price_alert: user alert triggered
        - heartbeat: keepalive every 30s

    Client can send:
        - {"type": "subscribe", "coins": ["BTC", "ETH"]} — filter by coins
        - {"type": "ping"} — request heartbeat
    """
    user = None
    user_id = None
    subscribed_coins: set[str] = set()

    # Wait for auth message (timeout 10s)
    try:
        await ws.accept()
        import asyncio
        raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        msg = _json.loads(raw)

        if msg.get("type") != "auth" or not msg.get("key"):
            await ws.send_json({"type": "error", "message": "First message must be auth"})
            await ws.close(code=4001)
            return

        # Validate key
        key_hash = hashlib.sha256(msg["key"].encode()).hexdigest()
        async with async_session() as session:
            result = await session.execute(
                select(UserApiKey)
                .where(UserApiKey.key_hash == key_hash, UserApiKey.is_active == True)
            )
            api_key_obj = result.scalar_one_or_none()

            if not api_key_obj or not api_key_obj.user:
                await ws.send_json({"type": "error", "message": "Invalid API key"})
                await ws.close(code=4003)
                return

            user = api_key_obj.user
            user_id = user.id

            if user.is_banned or not user.is_active:
                await ws.send_json({"type": "error", "message": "Account suspended"})
                await ws.close(code=4003)
                return

        # Auth OK
        await ws.send_json({
            "type": "auth_ok",
            "tier": user.tier.value,
            "features": _get_tier_features(user.tier),
        })

    except asyncio.TimeoutError:
        try:
            await ws.send_json({"type": "error", "message": "Auth timeout"})
            await ws.close(code=4001)
        except Exception:
            pass
        return
    except Exception as e:
        try:
            await ws.close(code=4000)
        except Exception:
            pass
        return

    # Register connection
    # Re-accept not needed since we already accepted above
    # Just register in manager
    if user_id not in ws_manager.active:
        ws_manager.active[user_id] = []
    ws_manager.active[user_id].append(ws)
    ws_manager._user_tiers[user_id] = user.tier
    logger.info(f"WS authenticated: user {user_id} ({user.tier.value})")

    try:
        # Start heartbeat task
        import asyncio

        async def _heartbeat():
            while True:
                await asyncio.sleep(30)
                try:
                    await ws.send_json({"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    break

        hb_task = asyncio.create_task(_heartbeat())

        # Message loop
        while True:
            raw = await ws.receive_text()
            msg = _json.loads(raw)

            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})
            elif msg.get("type") == "subscribe":
                coins = msg.get("coins", [])
                if isinstance(coins, list):
                    subscribed_coins = {c.upper() for c in coins if isinstance(c, str)}
                    ws_manager.set_subscribed_coins(user_id, subscribed_coins)
                    await ws.send_json({"type": "subscribed", "coins": list(subscribed_coins)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS error for user {user_id}: {e}")
    finally:
        hb_task.cancel()
        ws_manager.disconnect(ws, user_id)
