"""
Admin panel router — SSR with Jinja2 templates.
All pages protected by cookie-based session auth.

Optimizations:
- TTL in-memory cache (30-60s) for heavy aggregate queries
- Merged COUNT queries via CASE expressions (11→2 on dashboard)
- asyncio.gather for independent I/O on system page
- Exchange pings cached & parallelized with timeout
- No double-fetch on signal detail (selectin already loads updates)
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from sqlalchemy import select, func, and_, or_, desc, case, String, text, literal_column

from app.config import settings
from app.database import async_session
from app.models import (
    Signal, SignalStatus, SignalDirection, SignalUpdate, UpdateType,
    User, Tier, Language, Subscription,
    AIFeedback, VectorMemory,
    UserAlert, AlertLog, AlertType,
    MarketSnapshot, CandleRecord, CandleTimeframe, CoinMeta, DailyAIAnalysis,
)

from app.admin.auth import (
    get_current_admin, verify_login, create_session,
    _check_rate_limit, _record_attempt, _clear_attempts, _get_client_ip,
)

router = APIRouter(prefix="/admin", tags=["admin-panel"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


# ─── TTL Cache ──────────────────────────────────────────

_cache: dict[str, tuple[float, Any]] = {}


def _get_cached(key: str, ttl: float = 30.0) -> Any | None:
    """Return cached value if fresh, else None."""
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < ttl:
        return entry[1]
    return None


def _set_cached(key: str, value: Any) -> Any:
    _cache[key] = (time.monotonic(), value)
    return value


# ─── Helpers ────────────────────────────────────────────

from markupsafe import Markup

def _status_badge(status: str) -> str:
    m = {
        "active": ("badge-active", "Active"),
        "tp1_hit": ("badge-tp", "TP1 ✓"),
        "tp2_hit": ("badge-tp", "TP2 ✓"),
        "tp3_hit": ("badge-tp", "TP3 ✓"),
        "stopped": ("badge-stopped", "SL ✗"),
        "expired": ("badge-expired", "Expired"),
        "closed": ("badge-expired", "Closed"),
        "cancelled": ("badge-expired", "Cancelled"),
    }
    cls, label = m.get(status, ("badge-secondary", status))
    return Markup(f'<span class="badge {cls}">{label}</span>')

def _direction_badge(direction: str) -> str:
    if direction == "long":
        return Markup('<span class="badge badge-long">LONG</span>')
    return Markup('<span class="badge badge-short">SHORT</span>')

def _tier_badge(tier: str) -> str:
    m = {"free": "secondary", "pro": "info", "elite": "warning"}
    return Markup(f'<span class="badge bg-{m.get(tier, "secondary")}">{tier.upper()}</span>')


def _pnl_color(pnl) -> str:
    if pnl is None:
        return ""
    return "text-green" if pnl > 0 else "text-red" if pnl < 0 else ""


def _fmt_price(price) -> str:
    if price is None:
        return "—"
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:,.6g}"


def _fmt_pct(pct) -> str:
    if pct is None:
        return "—"
    return f"{pct:+.2f}%"


def _time_ago(dt) -> str:
    if not dt:
        return "—"
    diff = datetime.now(timezone.utc) - dt
    if diff.days > 0:
        return f"{diff.days}д тому"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours}г тому"
    minutes = diff.seconds // 60
    return f"{minutes}хв тому"


# Register template filters
templates.env.filters["status_badge"] = _status_badge
templates.env.filters["direction_badge"] = _direction_badge
templates.env.filters["tier_badge"] = _tier_badge
templates.env.filters["pnl_color"] = _pnl_color
templates.env.filters["fmt_price"] = _fmt_price
templates.env.filters["fmt_pct"] = _fmt_pct
templates.env.filters["time_ago"] = _time_ago


def _admin_or_redirect(request: Request):
    admin = get_current_admin(request)
    if not admin:
        return None
    return admin


# ─── Auth Routes ────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_admin(request):
        return RedirectResponse("/admin/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    ip = _get_client_ip(request)

    if not _check_rate_limit(ip):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Занадто багато спроб. Зачекайте 5 хвилин.",
        })

    if verify_login(username, password):
        _clear_attempts(ip)
        token = create_session(username)
        response = RedirectResponse("/admin/", status_code=302)
        response.set_cookie(
            "admin_session", token,
            httponly=True, samesite="lax", secure=True, max_age=86400,
        )
        return response

    _record_attempt(ip)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Невірний логін або пароль",
    })


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


# ─── Dashboard ──────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    cached = _get_cached("dashboard", ttl=30)
    if cached:
        cached["request"] = request
        cached["admin_user"] = admin["user"]
        return templates.TemplateResponse("dashboard.html", cached)

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    async with async_session() as session:
        # ── 1 query: all signal aggregates via CASE ──
        sig_row = (await session.execute(
            select(
                func.count(Signal.id).label("total"),
                func.count(case((Signal.status == SignalStatus.ACTIVE, Signal.id))).label("active"),
                func.count(case((Signal.created_at >= day_ago, Signal.id))).label("today"),
                # Wins = TP hits + CLOSED with positive PnL (partial wins)
                func.count(case((
                    and_(Signal.created_at >= week_ago,
                         or_(
                             Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT]),
                             and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent > 0),
                         )),
                    Signal.id,
                ))).label("wins_7d"),
                # Losses = STOPPED + CLOSED with negative PnL
                func.count(case((
                    and_(Signal.created_at >= week_ago,
                         or_(
                             Signal.status == SignalStatus.STOPPED,
                             and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent <= 0),
                         )),
                    Signal.id,
                ))).label("losses_7d"),
                func.avg(case((
                    and_(Signal.created_at >= week_ago, Signal.pnl_percent.isnot(None)),
                    Signal.pnl_percent,
                ))).label("avg_pnl_7d"),
                # Total PnL (all time)
                func.sum(case((
                    Signal.pnl_percent.isnot(None),
                    Signal.pnl_percent,
                ))).label("total_pnl"),
                # TP hit rates (all time, for closed signals)
                func.count(case((
                    Signal.status.in_([
                        SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                        SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED,
                    ]),
                    Signal.id,
                ))).label("total_closed"),
                func.count(case((
                    or_(
                        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT]),
                        and_(Signal.status == SignalStatus.CLOSED, Signal.pnl_percent > 0),
                    ),
                    Signal.id,
                ))).label("total_wins"),
                # Best/worst trade
                func.max(Signal.pnl_percent).label("best_pnl"),
                func.min(case((Signal.pnl_percent.isnot(None), Signal.pnl_percent))).label("worst_pnl"),
                # Long/Short counts
                func.count(case((Signal.direction == SignalDirection.LONG, Signal.id))).label("long_count"),
                func.count(case((Signal.direction == SignalDirection.SHORT, Signal.id))).label("short_count"),
            )
        )).one()

        # ── 2 query: all user aggregates via CASE ──
        usr_row = (await session.execute(
            select(
                func.count(User.id).label("total"),
                func.count(case((User.tier == Tier.PRO, User.id))).label("pro"),
                func.count(case((User.tier == Tier.ELITE, User.id))).label("elite"),
            )
        )).one()

        # ── 3 query: recent signals (lightweight, uses index) ──
        recent_signals = (await session.execute(
            select(Signal).order_by(desc(Signal.created_at)).limit(10)
        )).scalars().all()

        # ── 4 query: active alerts count ──
        active_alerts = await session.scalar(
            select(func.count(UserAlert.id)).where(UserAlert.is_active == True)
        ) or 0

    wins_7d = sig_row.wins_7d or 0
    losses_7d = sig_row.losses_7d or 0
    total_closed_7d = wins_7d + losses_7d
    total_closed = sig_row.total_closed or 0
    total_wins = sig_row.total_wins or 0

    # System health (cheap in-process calls)
    redis_ok = False
    last_scan = None
    try:
        from app.redis_client import get_scan_heartbeat, redis_client
        redis_ok = redis_client is not None
        last_scan = await get_scan_heartbeat()
    except Exception:
        pass

    scheduler_running = False
    scheduler_jobs = 0
    try:
        from app.scheduler import scheduler as _sched
        scheduler_running = _sched.running
        scheduler_jobs = len(_sched.get_jobs())
    except Exception:
        pass

    ctx = {
        "active_page": "dashboard",
        "total_signals": sig_row.total or 0,
        "active_signals": sig_row.active or 0,
        "signals_today": sig_row.today or 0,
        "wins_7d": wins_7d,
        "losses_7d": losses_7d,
        "win_rate_7d": round(wins_7d / total_closed_7d * 100, 1) if total_closed_7d > 0 else 0,
        "avg_pnl_7d": round(sig_row.avg_pnl_7d or 0, 2),
        "total_pnl": round(sig_row.total_pnl or 0, 2),
        "total_closed": total_closed,
        "total_wins": total_wins,
        "win_rate_all": round(total_wins / total_closed * 100, 1) if total_closed > 0 else 0,
        "best_pnl": round(sig_row.best_pnl or 0, 2),
        "worst_pnl": round(sig_row.worst_pnl or 0, 2),
        "long_count": sig_row.long_count or 0,
        "short_count": sig_row.short_count or 0,
        "total_users": usr_row.total or 0,
        "pro_users": usr_row.pro or 0,
        "elite_users": usr_row.elite or 0,
        "active_alerts": active_alerts,
        "recent_signals": recent_signals,
        "redis_ok": redis_ok,
        "scheduler_running": scheduler_running,
        "scheduler_jobs": scheduler_jobs,
        "last_scan": last_scan,
        "dry_run": settings.DRY_RUN,
    }
    _set_cached("dashboard", ctx)
    ctx["request"] = request
    ctx["admin_user"] = admin["user"]
    return templates.TemplateResponse("dashboard.html", ctx)


# ─── Signals ────────────────────────────────────────────

@router.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request, status: str = "", coin: str = "", page: int = 1, cleaned: str = ""):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    per_page = 30
    offset = (page - 1) * per_page

    async with async_session() as session:
        q = select(Signal)
        count_q = select(func.count(Signal.id))

        if status:
            try:
                s = SignalStatus(status)
                q = q.where(Signal.status == s)
                count_q = count_q.where(Signal.status == s)
            except ValueError:
                pass
        if coin:
            q = q.where(Signal.coin_symbol.ilike(f"%{coin}%"))
            count_q = count_q.where(Signal.coin_symbol.ilike(f"%{coin}%"))

        total = await session.scalar(count_q) or 0
        result = await session.execute(
            q.order_by(desc(Signal.created_at)).offset(offset).limit(per_page)
        )
        signals = result.scalars().all()

        # Cleanup counts
        count_stopped = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.STOPPED)
        ) or 0
        count_expired = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.EXPIRED)
        ) or 0
        count_closed = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.CLOSED)
        ) or 0
        count_cancelled = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.CANCELLED)
        ) or 0

    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse("signals.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "signals",
        "signals": signals,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "filter_status": status,
        "filter_coin": coin,
        "statuses": [s.value for s in SignalStatus],
        "count_stopped": count_stopped,
        "count_expired": count_expired,
        "count_closed": count_closed,
        "count_cancelled": count_cancelled,
        "cleaned": int(cleaned) if cleaned.isdigit() else None,
    })


@router.get("/signals/{signal_id}", response_class=HTMLResponse)
async def signal_detail(request: Request, signal_id: int):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if not signal:
            return RedirectResponse("/admin/signals", status_code=302)
        # updates already loaded via selectin relationship — no extra query
        updates = list(reversed(signal.updates)) if signal.updates else []

    return templates.TemplateResponse("signal_detail.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "signals",
        "signal": signal,
        "updates": updates,
    })


@router.post("/signals/{signal_id}/cancel")
async def signal_cancel(request: Request, signal_id: int):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if signal and signal.status in (SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT):
            signal.status = SignalStatus.CANCELLED
            signal.closed_at = datetime.now(timezone.utc)
            update = SignalUpdate(
                signal_id=signal_id,
                update_type=UpdateType.CANCEL,
                price_at_update=signal.entry_price,
                details={"admin": admin["user"], "reason": "Скасовано через адмінку"},  # type: ignore[arg-type]
            )
            session.add(update)
            await session.commit()
            logger.info(f"Admin {admin['user']} cancelled signal #{signal_id}")
            _cache.pop("dashboard", None)

    return RedirectResponse(f"/admin/signals/{signal_id}", status_code=302)


@router.post("/signals/cleanup")
async def signals_cleanup(request: Request, status_filter: str = Form(...)):
    """Delete closed signals by status category."""
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    from sqlalchemy import delete as sa_delete

    status_map = {
        "stopped": [SignalStatus.STOPPED],
        "expired": [SignalStatus.EXPIRED],
        "closed": [SignalStatus.CLOSED],
        "cancelled": [SignalStatus.CANCELLED],
        "all_closed": [SignalStatus.STOPPED, SignalStatus.EXPIRED, SignalStatus.CLOSED, SignalStatus.CANCELLED],
    }
    statuses = status_map.get(status_filter, [])
    deleted = 0
    if statuses:
        async with async_session() as session:
            result = await session.execute(
                sa_delete(Signal).where(Signal.status.in_(statuses))
            )
            deleted = result.rowcount
            await session.commit()
        logger.info(f"Admin {admin['user']} cleaned up {deleted} signals (filter={status_filter})")
        _cache.pop("dashboard", None)

    return RedirectResponse(f"/admin/signals?cleaned={deleted}", status_code=302)


# ─── Users ──────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, q: str = "", tier: str = "", page: int = 1):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    per_page = 30
    offset = (page - 1) * per_page

    async with async_session() as session:
        query = select(User)
        count_q = select(func.count(User.id))

        if q:
            query = query.where(
                User.username.ilike(f"%{q}%") | User.first_name.ilike(f"%{q}%") |
                User.telegram_id.cast(String).like(f"%{q}%")
            )
            count_q = count_q.where(
                User.username.ilike(f"%{q}%") | User.first_name.ilike(f"%{q}%") |
                User.telegram_id.cast(String).like(f"%{q}%")
            )
        if tier:
            try:
                t = Tier(tier)
                query = query.where(User.tier == t)
                count_q = count_q.where(User.tier == t)
            except ValueError:
                pass

        total = await session.scalar(count_q) or 0
        result = await session.execute(
            query.order_by(desc(User.created_at)).offset(offset).limit(per_page)
        )
        users = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page

    return templates.TemplateResponse("users.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "users",
        "users": users,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "filter_q": q,
        "filter_tier": tier,
        "tiers": [t.value for t in Tier],
    })


@router.post("/users/{user_id}/ban")
async def user_ban(request: Request, user_id: int):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.is_banned = not user.is_banned
            await session.commit()
            logger.info(f"Admin {admin['user']} {'banned' if user.is_banned else 'unbanned'} user {user.telegram_id}")

    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/tier")
async def user_change_tier(request: Request, user_id: int, new_tier: str = Form(...)):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            try:
                user.tier = Tier(new_tier)
                await session.commit()
                logger.info(f"Admin {admin['user']} changed user {user.telegram_id} tier to {new_tier}")
            except ValueError:
                pass

    return RedirectResponse("/admin/users", status_code=302)


# ─── AI Learning ────────────────────────────────────────

@router.get("/learning", response_class=HTMLResponse)
async def learning_page(request: Request):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    cached = _get_cached("learning", ttl=30)
    if cached:
        cached["request"] = request
        cached["admin_user"] = admin["user"]
        return templates.TemplateResponse("learning.html", cached)

    async with async_session() as session:
        # ── 1 query: feedback counts via CASE ──
        fb_row = (await session.execute(
            select(
                func.count(AIFeedback.id).label("total"),
                func.count(case((AIFeedback.applied == True, AIFeedback.id))).label("applied"),
            )
        )).one()
        total_fb = fb_row.total or 0
        applied_fb = fb_row.applied or 0

        # ── 2 query: recent feedbacks ──
        feedbacks = (await session.execute(
            select(AIFeedback).order_by(desc(AIFeedback.created_at)).limit(30)
        )).scalars().all()

        # ── 3 query: lessons + adjustments (single query, split in Python) ──
        mem_res = (await session.execute(
            select(VectorMemory)
            .where(VectorMemory.category.in_(["lesson_learned", "system_adjustment", "pattern_insight"]))
            .order_by(desc(VectorMemory.created_at))
            .limit(30)
        )).scalars().all()
        lessons = mem_res
        adjustments = [m for m in mem_res if m.category == "system_adjustment"][:10]

        # ── 4 query: feedback type breakdown ──
        fb_types = {}
        for row in (await session.execute(
            select(AIFeedback.feedback_type, func.count(AIFeedback.id))
            .group_by(AIFeedback.feedback_type)
        )).all():
            fb_types[row[0]] = row[1]

    # System health (has its own internal queries)
    health = {}
    try:
        from app.ai.learning import self_learning
        health = await self_learning.get_system_health()
    except Exception as e:
        logger.debug(f"Learning health fetch failed: {e}")

    ctx = {
        "active_page": "learning",
        "feedbacks": feedbacks,
        "total_fb": total_fb,
        "applied_fb": applied_fb,
        "unapplied_fb": total_fb - applied_fb,
        "fb_types": fb_types,
        "lessons": lessons,
        "adjustments": adjustments,
        "health": health,
    }
    _set_cached("learning", ctx)
    ctx["request"] = request
    ctx["admin_user"] = admin["user"]
    return templates.TemplateResponse("learning.html", ctx)


@router.post("/learning/run-cycle")
async def run_learning_cycle(request: Request):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    try:
        from app.ai.learning import self_learning
        await self_learning.apply_accumulated_corrections()
        logger.info(f"Admin {admin['user']} triggered learning cycle")
    except Exception as e:
        logger.error(f"Manual learning cycle failed: {e}")

    _cache.pop("learning", None)  # invalidate so next load shows fresh data
    return RedirectResponse("/admin/learning", status_code=302)


# ─── Stats ──────────────────────────────────────────────

@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request, period: str = "7d"):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    cache_key = f"stats:{period}"
    cached = _get_cached(cache_key, ttl=60)
    if cached:
        cached["request"] = request
        cached["admin_user"] = admin["user"]
        return templates.TemplateResponse("stats.html", cached)

    days = {"1d": 1, "7d": 7, "30d": 30, "90d": 90, "all": None}.get(period, 7)

    # Run compute_stats, leaderboard, and exchange_stats concurrently
    async def _compute():
        try:
            from app.stats.calculator import compute_stats
            return await compute_stats(period_days=days) if days else await compute_stats()
        except Exception as e:
            logger.error(f"Stats computation failed: {e}")
            return None

    async def _leaderboard():
        try:
            from app.stats.reports import get_leaderboard
            return await get_leaderboard(limit=15)
        except Exception:
            return []

    async def _exchange_stats():
        result_list = []
        async with async_session() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
            q = select(
                Signal.exchange,
                func.count(Signal.id).label("total"),
                func.count(case(
                    (Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT]), Signal.id),
                )).label("wins"),
                func.avg(Signal.pnl_percent).label("avg_pnl"),
            ).where(Signal.pnl_percent.isnot(None))
            if cutoff:
                q = q.where(Signal.created_at >= cutoff)
            q = q.group_by(Signal.exchange)
            for row in (await session.execute(q)).all():
                wr = round(row.wins / row.total * 100, 1) if row.total > 0 else 0
                result_list.append({
                    "exchange": row.exchange, "total": row.total,
                    "wins": row.wins, "win_rate": wr,
                    "avg_pnl": round(row.avg_pnl or 0, 2),
                })
        return result_list

    stats, leaderboard, exchange_stats = await asyncio.gather(
        _compute(), _leaderboard(), _exchange_stats()
    )

    ctx = {
        "active_page": "stats",
        "stats": stats,
        "period": period,
        "leaderboard": leaderboard,
        "exchange_stats": exchange_stats,
    }
    _set_cached(cache_key, ctx)
    ctx["request"] = request
    ctx["admin_user"] = admin["user"]
    return templates.TemplateResponse("stats.html", ctx)


# ─── Alerts ─────────────────────────────────────────────

@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    cached = _get_cached("alerts", ttl=30)
    if cached:
        cached["request"] = request
        cached["admin_user"] = admin["user"]
        return templates.TemplateResponse("alerts.html", cached)

    async with async_session() as session:
        # ── 1 query: all counts via CASE ──
        cnt_row = (await session.execute(
            select(
                func.count(UserAlert.id).label("total"),
                func.count(case((UserAlert.is_active == True, UserAlert.id))).label("active"),
            )
        )).one()
        total_triggers = await session.scalar(select(func.count(AlertLog.id))) or 0

        # ── 2 query: recent alerts ──
        alerts = (await session.execute(
            select(UserAlert).order_by(desc(UserAlert.created_at)).limit(50)
        )).scalars().all()

        # ── 3 query: recent logs ──
        logs = (await session.execute(
            select(AlertLog).order_by(desc(AlertLog.created_at)).limit(50)
        )).scalars().all()

        # ── 4 query: type breakdown ──
        type_counts = {}
        for row in (await session.execute(
            select(UserAlert.alert_type, func.count(UserAlert.id))
            .group_by(UserAlert.alert_type)
        )).all():
            type_counts[row[0].value if hasattr(row[0], 'value') else row[0]] = row[1]

    ctx = {
        "active_page": "alerts",
        "alerts": alerts,
        "logs": logs,
        "total_alerts": cnt_row.total or 0,
        "active_alerts": cnt_row.active or 0,
        "total_triggers": total_triggers,
        "type_counts": type_counts,
    }
    _set_cached("alerts", ctx)
    ctx["request"] = request
    ctx["admin_user"] = admin["user"]
    return templates.TemplateResponse("alerts.html", ctx)


# ─── System ─────────────────────────────────────────────

_TABLE_MODELS = [
    ("signals", Signal), ("users", User), ("subscriptions", Subscription),
    ("snapshots", MarketSnapshot), ("candles", CandleRecord),
    ("coin_meta", CoinMeta), ("ai_feedback", AIFeedback),
    ("vector_memory", VectorMemory), ("alerts", UserAlert),
    ("alert_logs", AlertLog), ("daily_analysis", DailyAIAnalysis),
]


async def _fetch_db_stats() -> tuple[bool, dict[str, int]]:
    """Single session: health check + all table counts in one round-trip."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))

            # Build single query: SELECT count(*) FILTER (WHERE ...) for each table
            # PostgreSQL supports this, but for portability use UNION ALL approach
            counts: dict[str, int] = {}
            # Batch all counts in a single query via subselects
            cols = []
            for name, model in _TABLE_MODELS:
                cols.append(
                    select(func.count(model.id)).correlate(None).scalar_subquery().label(name)
                )
            row = (await session.execute(select(*cols))).one()
            for name, _ in _TABLE_MODELS:
                counts[name] = getattr(row, name, 0) or 0
            return True, counts
    except Exception as e:
        logger.debug(f"DB stats error: {e}")
        return False, {}


async def _fetch_redis_info() -> tuple[bool, dict]:
    """Single Redis INFO call for memory + clients + dbsize."""
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        if not r:
            return False, {}
        info = await r.info()  # full info in one call
        keys = await r.dbsize()
        return True, {
            "used_memory": info.get("used_memory_human", "?"),
            "connected_clients": info.get("connected_clients", 0),
            "total_keys": keys,
        }
    except Exception:
        return False, {}


async def _fetch_exchange_status() -> dict:
    """Ping all exchanges in parallel with 3s timeout, cached 60s."""
    cached = _get_cached("exchange_pings", ttl=60)
    if cached is not None:
        return cached

    status = {}
    try:
        from app.exchanges.manager import exchange_manager
        names = list(exchange_manager.exchanges.keys())

        async def _ping(name: str):
            try:
                ex = exchange_manager.get_exchange(name)
                ticker = await asyncio.wait_for(ex.get_ticker("BTCUSDT"), timeout=3.0)
                return name, {"ok": True, "price": ticker.last_price}
            except Exception:
                return name, {"ok": False, "price": None}

        results = await asyncio.gather(*[_ping(n) for n in names])
        for n, s in results:
            status[n] = s
    except Exception:
        pass

    _set_cached("exchange_pings", status)
    return status


@router.get("/system", response_class=HTMLResponse)
async def system_page(request: Request):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    cached = _get_cached("system", ttl=30)
    if cached:
        cached["request"] = request
        cached["admin_user"] = admin["user"]
        return templates.TemplateResponse("system.html", cached)

    # Run ALL I/O in parallel
    (db_ok, db_stats), (redis_ok, redis_info), exchange_status = await asyncio.gather(
        _fetch_db_stats(),
        _fetch_redis_info(),
        _fetch_exchange_status(),
    )

    # Scheduler (in-process, instant)
    scheduler_running = False
    jobs = []
    try:
        from app.scheduler import scheduler as _sched
        scheduler_running = _sched.running
        for job in _sched.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "next_run": next_run.strftime("%H:%M:%S") if next_run else "—",
                "trigger": str(job.trigger),
            })
    except Exception:
        pass

    # Scan heartbeat (cheap Redis GET)
    last_scan = None
    try:
        from app.redis_client import get_scan_heartbeat
        last_scan = await get_scan_heartbeat()
    except Exception:
        pass

    env_config = {
        "ENVIRONMENT": settings.ENVIRONMENT,
        "DRY_RUN": settings.DRY_RUN,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "CHANNELS": len(settings.all_channel_ids),
        "ADMIN_IDS": len(settings.admin_ids),
    }

    ctx = {
        "active_page": "system",
        "db_ok": db_ok,
        "db_stats": db_stats,
        "redis_ok": redis_ok,
        "redis_info": redis_info,
        "scheduler_running": scheduler_running,
        "jobs": jobs,
        "exchange_status": exchange_status,
        "last_scan": last_scan,
        "env_config": env_config,
    }
    _set_cached("system", ctx)
    ctx["request"] = request
    ctx["admin_user"] = admin["user"]
    return templates.TemplateResponse("system.html", ctx)


# ─── Signal Logs (dump for analysis) ────────────────────

def _format_signal_log(s: Signal) -> str:
    """Format a single signal as a plain-text log block."""
    lines = []
    result = "—"
    if s.status == SignalStatus.STOPPED:
        if s.pnl_percent is not None and s.pnl_percent > 0:
            result = "WIN (trailing SL)"
        else:
            result = "LOSS (SL hit)"
    elif s.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT, SignalStatus.CLOSED):
        if s.pnl_percent is not None and s.pnl_percent > 0:
            result = "WIN"
        elif s.pnl_percent is not None and s.pnl_percent < 0:
            result = "LOSS"
        else:
            result = s.status.value.upper()
    elif s.status == SignalStatus.ACTIVE:
        result = "ACTIVE"
    elif s.status == SignalStatus.CANCELLED:
        result = "CANCELLED"
    elif s.status == SignalStatus.EXPIRED:
        result = "EXPIRED"

    lines.append(f"═══ Signal #{s.id} | {s.coin_symbol} {s.direction.value.upper()} | {result} ═══")
    lines.append(f"  Exchange:    {s.exchange} | Pair: {s.pair} | TF: {s.timeframe}")
    lines.append(f"  Tier:        {s.min_tier.value if s.min_tier else 'free'}")
    lines.append(f"  Confidence:  {s.confidence_score:.1f}%" if s.confidence_score else "  Confidence:  —")
    lines.append(f"  Created:     {s.created_at.strftime('%d.%m.%Y %H:%M UTC') if s.created_at else '—'}")
    if s.closed_at:
        lines.append(f"  Closed:      {s.closed_at.strftime('%d.%m.%Y %H:%M UTC')}")
    lines.append(f"  Status:      {s.status.value}")
    lines.append("")

    lines.append(f"  Entry:       ${s.entry_price:,.8g}")
    if s.entry_zone_low and s.entry_zone_high:
        lines.append(f"  Entry Zone:  ${s.entry_zone_low:,.8g} — ${s.entry_zone_high:,.8g}")
    lines.append(f"  TP1:         ${s.tp1:,.8g}")
    if s.tp2:
        lines.append(f"  TP2:         ${s.tp2:,.8g}")
    if s.tp3:
        lines.append(f"  TP3:         ${s.tp3:,.8g}")
    lines.append(f"  Stop Loss:   ${s.stop_loss:,.8g}")
    if s.leverage_suggested:
        lines.append(f"  Leverage:    {s.leverage_suggested}x")
    if s.risk_percent:
        lines.append(f"  Risk:        {s.risk_percent:.1f}%")
    lines.append("")

    if s.entry_actual:
        lines.append(f"  Entry Actual: ${s.entry_actual:,.8g}")
    if s.exit_actual:
        lines.append(f"  Exit Actual:  ${s.exit_actual:,.8g}")
    if s.pnl_percent is not None:
        lines.append(f"  PnL:          {s.pnl_percent:+.2f}%")
    if s.peak_profit_percent is not None:
        lines.append(f"  Peak Profit:  {s.peak_profit_percent:+.2f}%")
    if s.max_drawdown_percent is not None:
        lines.append(f"  Max Drawdown: {s.max_drawdown_percent:+.2f}%")
    lines.append("")

    if s.ai_reasoning:
        lines.append(f"  AI Reasoning: {s.ai_reasoning}")

    if s.factors:
        lines.append(f"  Factors: {s.factors}")

    if s.updates:
        lines.append(f"  Updates ({len(s.updates)}):")
        for u in s.updates:
            ts = u.created_at.strftime('%d.%m %H:%M') if u.created_at else '?'
            price_str = f" @ ${u.price_at_update:,.8g}" if u.price_at_update else ""
            det = f" | {u.details}" if u.details else ""
            lines.append(f"    [{ts}] {u.update_type.value}{price_str}{det}")

    return "\n".join(lines)


@router.get("/signal-logs", response_class=HTMLResponse)
async def signal_logs_page(request: Request, n: int = 50, f: str = "all"):
    admin = _admin_or_redirect(request)
    if not admin:
        return RedirectResponse("/admin/login", status_code=302)

    n = min(max(n, 1), 200)

    async with async_session() as db:
        q = select(Signal).order_by(desc(Signal.created_at)).limit(n)

        if f == "closed":
            q = q.where(Signal.status.notin_([SignalStatus.ACTIVE, SignalStatus.CANCELLED]))
        elif f == "win":
            q = q.where(
                Signal.status.notin_([SignalStatus.ACTIVE, SignalStatus.CANCELLED]),
                Signal.pnl_percent > 0,
            )
        elif f == "loss":
            q = q.where(
                Signal.status.notin_([SignalStatus.ACTIVE, SignalStatus.CANCELLED]),
                Signal.pnl_percent < 0,
            )
        elif f == "active":
            q = q.where(Signal.status == SignalStatus.ACTIVE)

        result = await db.execute(q)
        signals = result.scalars().all()

    # Stats
    closed = [s for s in signals if s.status not in (SignalStatus.ACTIVE, SignalStatus.CANCELLED)]
    wins = sum(1 for s in closed if s.pnl_percent is not None and s.pnl_percent > 0)
    losses = sum(1 for s in closed if s.pnl_percent is not None and s.pnl_percent <= 0)
    total_closed = wins + losses
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
    pnl_values = [s.pnl_percent for s in closed if s.pnl_percent is not None]
    avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0.0
    total_pnl = sum(pnl_values)

    # Build text
    header_lines = [
        f"BLACK ROOM Signal Logs — {len(signals)} signals (filter: {f})",
        f"Generated: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}",
        f"Closed: {total_closed} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%",
        f"Avg PnL: {avg_pnl:+.2f}% | Total PnL: {total_pnl:+.2f}%",
        "═" * 70,
        "",
    ]
    log_blocks = [_format_signal_log(s) for s in signals]
    log_text = "\n".join(header_lines) + "\n\n".join(log_blocks)

    return templates.TemplateResponse("signal_logs.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "signal_logs",
        "n": n,
        "f": f,
        "total": len(signals),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "log_text": log_text,
    })


# ─── Coins (CoinMeta) Management ───────────────────────

@router.get("/coins")
async def coins_page(
    request: Request,
    q: str = "",
    status: str = "",
    page: int = 1,
):
    admin = _admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin

    per_page = 50
    offset = (max(1, page) - 1) * per_page

    async with async_session() as session:
        # Base query
        base_q = select(CoinMeta)
        count_q = select(func.count(CoinMeta.id))

        # Search filter
        if q:
            like = f"%{q}%"
            flt = or_(CoinMeta.symbol.ilike(like), CoinMeta.name.ilike(like))
            base_q = base_q.where(flt)
            count_q = count_q.where(flt)

        # Status filter
        if status == "no_logo":
            flt2 = and_(CoinMeta.logo_url.is_(None), CoinMeta.logo_thumb_url.is_(None))
            base_q = base_q.where(flt2)
            count_q = count_q.where(flt2)
        elif status == "no_name":
            base_q = base_q.where(CoinMeta.name.is_(None))
            count_q = count_q.where(CoinMeta.name.is_(None))
        elif status == "no_coingecko":
            base_q = base_q.where(CoinMeta.coingecko_id.is_(None))
            count_q = count_q.where(CoinMeta.coingecko_id.is_(None))
        elif status == "complete":
            flt2 = and_(
                CoinMeta.logo_url.isnot(None),
                CoinMeta.name.isnot(None),
                CoinMeta.coingecko_id.isnot(None),
            )
            base_q = base_q.where(flt2)
            count_q = count_q.where(flt2)

        total = await session.scalar(count_q) or 0
        total_pages = max(1, (total + per_page - 1) // per_page)

        result = await session.execute(
            base_q.order_by(CoinMeta.market_cap_rank.asc().nullslast(), CoinMeta.symbol.asc())
            .offset(offset).limit(per_page)
        )
        coins = result.scalars().all()

        # Stats
        with_logo = await session.scalar(
            select(func.count(CoinMeta.id)).where(
                or_(CoinMeta.logo_url.isnot(None), CoinMeta.logo_thumb_url.isnot(None))
            )
        ) or 0
        total_all = await session.scalar(select(func.count(CoinMeta.id))) or 0
        without_logo = total_all - with_logo
        without_cg = await session.scalar(
            select(func.count(CoinMeta.id)).where(CoinMeta.coingecko_id.is_(None))
        ) or 0

    return templates.TemplateResponse("coins.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "coins",
        "coins": coins,
        "total": total,
        "page": max(1, page),
        "total_pages": total_pages,
        "filter_q": q,
        "filter_status": status,
        "with_logo": with_logo,
        "without_logo": without_logo,
        "without_cg": without_cg,
    })


@router.post("/coins/{coin_id}/edit")
async def edit_coin(request: Request, coin_id: int):
    admin = _admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin

    form = await request.form()

    async with async_session() as session:
        coin = await session.get(CoinMeta, coin_id)
        if not coin:
            return RedirectResponse("/admin/coins", status_code=303)

        # Update text fields (empty string → None)
        for field in ("name", "coingecko_id", "logo_url", "logo_thumb_url", "homepage_url", "description_en"):
            val = form.get(field, "").strip()
            setattr(coin, field, val if val else None)

        # Update numeric fields
        for field in ("market_cap", "circulating_supply", "total_supply", "max_supply", "ath", "atl"):
            val = form.get(field, "").strip()
            if val:
                try:
                    setattr(coin, field, float(val))
                except ValueError:
                    pass
            else:
                setattr(coin, field, None)

        # Market cap rank (int)
        rank_val = form.get("market_cap_rank", "").strip()
        if rank_val:
            try:
                coin.market_cap_rank = int(rank_val)
            except ValueError:
                pass
        else:
            coin.market_cap_rank = None

        session.add(coin)
        await session.commit()

    logger.info(f"Admin edited coin {coin_id} ({form.get('name', '')})")
    return RedirectResponse(f"/admin/coins?q={coin.symbol.replace('USDT', '')}", status_code=303)


# ─── Wallets (Tracked Wallets) Management ──────────────

@router.get("/wallets")
async def wallets_page(
    request: Request,
    q: str = "",
    chain: str = "",
    page: int = 1,
):
    admin = _admin_or_redirect(request)
    if isinstance(admin, RedirectResponse):
        return admin

    from app.models import TrackedWallet, User, ChainType

    per_page = 50
    offset = (max(1, page) - 1) * per_page

    async with async_session() as session:
        base_q = select(TrackedWallet)
        count_q = select(func.count(TrackedWallet.id))

        if q:
            like = f"%{q}%"
            flt = or_(
                TrackedWallet.address.ilike(like),
                TrackedWallet.label.ilike(like),
            )
            base_q = base_q.where(flt)
            count_q = count_q.where(flt)

        if chain:
            try:
                chain_enum = ChainType(chain.lower())
                base_q = base_q.where(TrackedWallet.chain == chain_enum)
                count_q = count_q.where(TrackedWallet.chain == chain_enum)
            except ValueError:
                pass

        total = await session.scalar(count_q) or 0
        total_pages = max(1, (total + per_page - 1) // per_page)

        result = await session.execute(
            base_q.order_by(TrackedWallet.created_at.desc())
            .offset(offset).limit(per_page)
        )
        wallets = result.scalars().all()

        # Enrich with user info
        user_ids = list({w.user_id for w in wallets})
        users_map = {}
        if user_ids:
            u_result = await session.execute(
                select(User).where(User.id.in_(user_ids))
            )
            for u in u_result.scalars().all():
                users_map[u.id] = u

        for w in wallets:
            w.user_info = users_map.get(w.user_id)

        # Stats
        total_wallets = await session.scalar(select(func.count(TrackedWallet.id))) or 0
        active_wallets = await session.scalar(
            select(func.count(TrackedWallet.id)).where(TrackedWallet.is_active == True)
        ) or 0
        total_value = await session.scalar(
            select(func.coalesce(func.sum(TrackedWallet.total_value_usd), 0))
            .where(TrackedWallet.is_active == True)
        ) or 0
        unique_users = await session.scalar(
            select(func.count(func.distinct(TrackedWallet.user_id)))
        ) or 0

        # Chain distribution
        chain_rows = await session.execute(
            select(TrackedWallet.chain, func.count(TrackedWallet.id))
            .where(TrackedWallet.is_active == True)
            .group_by(TrackedWallet.chain)
        )
        chain_stats = {row[0].value: row[1] for row in chain_rows.all()}

    return templates.TemplateResponse("wallets.html", {
        "request": request,
        "admin_user": admin["user"],
        "active_page": "wallets",
        "wallets": wallets,
        "total": total,
        "page": max(1, page),
        "total_pages": total_pages,
        "filter_q": q,
        "filter_chain": chain,
        "total_wallets": total_wallets,
        "active_wallets": active_wallets,
        "total_value": total_value,
        "unique_users": unique_users,
        "chain_stats": chain_stats,
    })
