"""
Admin handler — system stats, user management, force scan, broadcast.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func

from app.config import settings
from app.database import async_session
from app.models import User, Signal, SignalStatus, Tier
from app.localization.texts import t
from app.bot.keyboards.inline import admin_kb, admin_cleanup_kb, admin_cleanup_confirm_kb
from app.bot.utils import answer_callback, safe_delete

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, db_user: User, lang: str):
    """Admin panel entry."""
    if not _is_admin(message.from_user.id):
        await message.answer(t("admin_access_denied", lang))
        return

    await safe_delete(message)
    await message.answer(t("admin_panel_title", lang), reply_markup=admin_kb(lang), parse_mode="HTML")


@router.callback_query(F.data == "admin_system")
async def cb_admin_system(callback: CallbackQuery, db_user: User, lang: str):
    """Show system statistics."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        pro_users = await session.scalar(
            select(func.count(User.id)).where(User.tier == Tier.PRO)
        )
        elite_users = await session.scalar(
            select(func.count(User.id)).where(User.tier == Tier.ELITE)
        )
        total_signals = await session.scalar(select(func.count(Signal.id)))
        active_signals = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
        )

    text = (
        f"{t('admin_stats_title', lang)}\n\n"
        f"👥 {t('admin_total_users', lang)}: <b>{total_users}</b>\n"
        f"⭐ Pro: <b>{pro_users}</b>\n"
        f"💎 Elite: <b>{elite_users}</b>\n\n"
        f"📡 {t('total_signals', lang)}: <b>{total_signals}</b>\n"
        f"🟢 {t('admin_active_signals', lang)}: <b>{active_signals}</b>\n"
    )

    try:
        from app.ai.learning import self_learning
        health = await self_learning.get_system_health()
        text += (
            f"\n🧠 <b>{t('admin_ai_health', lang)}</b>\n"
            f"{t('admin_win_rate', lang)}: {health.get('win_rate', 'N/A')}%\n"
            f"{t('admin_min_confidence', lang)}: {health.get('min_confidence', 'N/A')}\n"
        )
    except Exception:
        text += f"\n🧠 {t('admin_ai_health', lang)}: {t('admin_ai_unavailable', lang)}\n"

    await answer_callback(callback, text, reply_markup=admin_kb(lang))


@router.callback_query(F.data == "admin_scan")
async def cb_admin_scan(callback: CallbackQuery, db_user: User, lang: str):
    """Force a signal scan."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    await callback.answer(t("admin_scan_started", lang))

    try:
        from app.signals.engine import signal_engine
        results = await signal_engine.scan_all_pairs()
        await answer_callback(
            callback,
            t("admin_scan_complete", lang, count=len(results)),
            reply_markup=admin_kb(lang),
        )
    except Exception as e:
        await answer_callback(callback, t("admin_scan_error", lang, error=str(e)), reply_markup=admin_kb(lang))


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery, db_user: User, lang: str):
    """Show recent users."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )
        users = result.scalars().all()

    text = f"{t('admin_users_title', lang)}\n\n"
    for u in users:
        text += (
            f"• {u.first_name or 'N/A'} (@{u.username or 'N/A'}) — "
            f"{u.tier.value} — {u.created_at.strftime('%d.%m.%Y')}\n"
        )

    await answer_callback(callback, text, reply_markup=admin_kb(lang))


@router.callback_query(F.data == "admin_ai")
async def cb_admin_ai(callback: CallbackQuery, db_user: User, lang: str):
    """Show AI health details."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    try:
        from app.ai.learning import self_learning
        health = await self_learning.get_system_health()

        text = f"{t('admin_ai_title', lang)}\n\n"
        for k, v in health.items():
            text += f"• {k}: <b>{v}</b>\n"
    except Exception as e:
        text = t("admin_ai_error", lang, error=str(e))

    await answer_callback(callback, text, reply_markup=admin_kb(lang))


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, db_user: User, lang: str):
    """Broadcast placeholder — requires FSM for message input."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    await answer_callback(
        callback,
        t("admin_broadcast_title", lang),
        reply_markup=admin_kb(lang),
    )


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, db_user: User, lang: str):
    """Return to admin panel."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return
    await answer_callback(callback, t("admin_panel_title", lang), reply_markup=admin_kb(lang))


@router.callback_query(F.data == "admin_cleanup")
async def cb_admin_cleanup(callback: CallbackQuery, db_user: User, lang: str):
    """Show signal cleanup menu."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    # Count signals by status
    async with async_session() as session:
        stopped = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.STOPPED)
        )
        expired = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.EXPIRED)
        )
        closed = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.CLOSED)
        )
        cancelled = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.CANCELLED)
        )

    text = (
        "🗑 <b>Очистка сигналів</b>\n\n"
        f"🛑 Stopped: <b>{stopped}</b>\n"
        f"⏰ Expired: <b>{expired}</b>\n"
        f"📋 Closed: <b>{closed}</b>\n"
        f"❌ Cancelled: <b>{cancelled}</b>\n"
        f"📊 Всього закритих: <b>{stopped + expired + closed + cancelled}</b>\n\n"
        "Оберіть що видалити:"
    )
    await answer_callback(callback, text, reply_markup=admin_cleanup_kb(lang))


@router.callback_query(F.data.in_({"adm_clean_stopped", "adm_clean_expired", "adm_clean_closed", "adm_clean_all_old"}))
async def cb_admin_cleanup_select(callback: CallbackQuery, db_user: User, lang: str):
    """Count and confirm cleanup."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    status_map = {
        "adm_clean_stopped": [SignalStatus.STOPPED],
        "adm_clean_expired": [SignalStatus.EXPIRED],
        "adm_clean_closed": [SignalStatus.CLOSED],
        "adm_clean_all_old": [SignalStatus.STOPPED, SignalStatus.EXPIRED, SignalStatus.CLOSED, SignalStatus.CANCELLED],
    }
    label_map = {
        "adm_clean_stopped": "Stopped",
        "adm_clean_expired": "Expired",
        "adm_clean_closed": "Closed",
        "adm_clean_all_old": "All closed",
    }
    statuses = status_map[callback.data]
    async with async_session() as session:
        count = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status.in_(statuses))
        )

    if count == 0:
        await answer_callback(
            callback,
            "ℹ️ Немає сигналів для видалення.",
            reply_markup=admin_cleanup_kb(lang),
        )
    else:
        action = callback.data.replace("adm_clean_", "")
        await answer_callback(
            callback,
            f"⚠️ Ви впевнені? Буде видалено <b>{count}</b> сигналів (<b>{label_map[callback.data]}</b>).\n\nЦю дію неможливо скасувати!",
            reply_markup=admin_cleanup_confirm_kb(action, lang),
        )


@router.callback_query(F.data.startswith("adm_clean_yes_"))
async def cb_admin_cleanup_confirm(callback: CallbackQuery, db_user: User, lang: str):
    """Execute signal cleanup after confirmation."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔")
        return

    from sqlalchemy import delete as sa_delete

    action = callback.data.replace("adm_clean_yes_", "")
    status_map = {
        "stopped": [SignalStatus.STOPPED],
        "expired": [SignalStatus.EXPIRED],
        "closed": [SignalStatus.CLOSED],
        "all_old": [SignalStatus.STOPPED, SignalStatus.EXPIRED, SignalStatus.CLOSED, SignalStatus.CANCELLED],
    }
    statuses = status_map.get(action, [])
    deleted = 0
    if statuses:
        async with async_session() as session:
            result = await session.execute(
                sa_delete(Signal).where(Signal.status.in_(statuses))
            )
            deleted = result.rowcount
            await session.commit()

    from loguru import logger
    logger.info(f"Admin {callback.from_user.id} cleaned up {deleted} signals (action={action})")

    await answer_callback(
        callback,
        f"✅ Видалено <b>{deleted}</b> сигналів.",
        reply_markup=admin_kb(lang),
    )
