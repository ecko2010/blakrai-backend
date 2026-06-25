"""
Signal handlers — active signals, signal history, signal details.
Now with image cards and interactive inline buttons.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy import select, desc, func

from app.database import async_session
from app.models import User, Signal, SignalStatus, SignalDirection, Tier, UserSignalAction
from app.localization.texts import t
from app.bot.keyboards.inline import signals_menu_kb, pagination_kb, main_menu_kb, signal_notification_kb
from app.bot.keyboards.reply import signals_reply_kb
from app.bot.utils import answer_callback, send_and_cleanup, safe_delete

router = Router()


@router.callback_query(F.data == "signals")
async def cb_signals_menu(callback: CallbackQuery, db_user: User, lang: str):
    """Show signals submenu + swap reply keyboard."""
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    await _send_or_edit(
        chat_id, callback.bot,
        text=t("signals_menu", lang),
        reply_markup=signals_menu_kb(lang),
        reply_kb=signals_reply_kb(lang),
    )


@router.callback_query(F.data == "active_signals")
async def cb_active_signals(callback: CallbackQuery, db_user: User, lang: str):
    """Show currently active signals with image cards."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .where(Signal.status.in_((
                SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT,
            )))
            .order_by(desc(Signal.created_at))
            .limit(10)
        )
        signals = result.scalars().all()

    if not signals:
        await answer_callback(callback, t("no_active_signals", lang), reply_markup=signals_menu_kb(lang))
        return

    text = t("active_signals_header", lang) + "\n\n"

    for sig in signals:
        direction_emoji = "🟢" if sig.direction == SignalDirection.LONG else "🔴"
        status_emoji = "🟡" if sig.status == SignalStatus.ACTIVE else "✅"
        pnl_text = ""
        if sig.peak_profit_percent and sig.peak_profit_percent > 0:
            pnl_text = f" | 📈 +{sig.peak_profit_percent:.1f}%"

        if _user_has_access(db_user, sig):
            text += (
                f"{status_emoji} {direction_emoji} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()}\n"
                f"   📍 ${sig.entry_price:,.6g} → 🎯 ${sig.tp1:,.6g}{pnl_text}\n"
                f"   💪 {sig.confidence_score:.0f}% | {sig.exchange} | {sig.status.value}\n\n"
            )
        else:
            text += (
                f"{status_emoji} {direction_emoji} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()}\n"
                f"   🔒 {t('upgrade_to_see', lang)}\n\n"
            )

    await answer_callback(callback, text, reply_markup=signals_menu_kb(lang))


@router.callback_query(F.data == "signal_history")
async def cb_signal_history(callback: CallbackQuery, db_user: User, lang: str):
    """Show recent closed signals with results."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .where(Signal.status.in_((
                SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED,
            )))
            .order_by(desc(Signal.closed_at))
            .limit(10)
        )
        signals = result.scalars().all()

    if not signals:
        await answer_callback(callback, t("no_signal_history", lang), reply_markup=signals_menu_kb(lang))
        return

    text = t("signal_history_header", lang) + "\n\n"

    for sig in signals:
        pnl = sig.pnl_percent or 0
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⏹"
        pnl_str = f"{'+' if pnl > 0 else ''}{pnl:.2f}%"

        text += (
            f"{emoji} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()} — "
            f"{pnl_str} ({sig.status.value})\n"
        )

    await answer_callback(callback, text, reply_markup=signals_menu_kb(lang))


@router.callback_query(F.data == "tracked_signals")
async def cb_tracked_signals(callback: CallbackQuery, db_user: User, lang: str):
    """Show signals the user has activated/tracked."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .join(UserSignalAction, UserSignalAction.signal_id == Signal.id)
            .where(UserSignalAction.user_id == db_user.id)
            .order_by(desc(Signal.created_at))
            .limit(15)
        )
        signals = result.scalars().all()

    if not signals:
        await answer_callback(callback, t("no_tracked_signals", lang), reply_markup=signals_menu_kb(lang))
        return

    text = t("tracked_signals_header", lang) + "\n\n"

    for sig in signals:
        direction_emoji = "🟢" if sig.direction == SignalDirection.LONG else "🔴"

        if sig.status in (SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED, SignalStatus.CANCELLED):
            status_emoji = "⏹"
        elif sig.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT):
            status_emoji = "✅"
        else:
            status_emoji = "🟡"

        pnl = sig.pnl_percent or sig.peak_profit_percent or 0
        pnl_text = f" | {'📈' if pnl > 0 else '📉'} {pnl:+.1f}%" if pnl else ""

        text += (
            f"{status_emoji} {direction_emoji} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()}\n"
            f"   📍 ${sig.entry_price:,.6g} → 🎯 ${sig.tp1:,.6g}{pnl_text}\n"
            f"   {sig.status.value} | {sig.exchange}\n\n"
        )

    await answer_callback(callback, text, reply_markup=signals_menu_kb(lang))


@router.callback_query(F.data == "signal_stats")
async def cb_signal_stats(callback: CallbackQuery, db_user: User, lang: str):
    """Show signal performance statistics."""
    async with async_session() as session:
        total = await session.scalar(select(func.count(Signal.id)))

        wins = await session.scalar(
            select(func.count(Signal.id)).where(
                Signal.status.in_((SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT))
            )
        )

        losses = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.STOPPED)
        )

        active = await session.scalar(
            select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
        )

        avg_conf = await session.scalar(select(func.avg(Signal.confidence_score)))

        tracked = await session.scalar(
            select(func.count(UserSignalAction.id)).where(
                UserSignalAction.user_id == db_user.id
            )
        )

        avg_pnl = await session.scalar(
            select(func.avg(Signal.pnl_percent)).where(
                Signal.pnl_percent.isnot(None),
                Signal.status.in_((
                    SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                    SignalStatus.STOPPED, SignalStatus.CLOSED,
                ))
            )
        )

    total = total or 0
    wins = wins or 0
    losses = losses or 0
    active = active or 0
    tracked = tracked or 0
    avg_conf = avg_conf or 0
    avg_pnl = avg_pnl or 0
    closed = wins + losses
    winrate = (wins / closed * 100) if closed > 0 else 0

    text = t("signal_stats_header", lang) + "\n\n"

    if lang == "uk":
        text += (
            f"📊 <b>Всього сигналів:</b> {total}\n"
            f"🟡 <b>Активних:</b> {active}\n"
            f"✅ <b>Виграшних:</b> {wins}\n"
            f"❌ <b>Програшних:</b> {losses}\n"
            f"🏆 <b>Вінрейт:</b> {winrate:.1f}%\n\n"
            f"📈 <b>Середній PnL:</b> {avg_pnl:+.2f}%\n"
            f"💪 <b>Середня впевненість:</b> {avg_conf:.0f}%\n\n"
            f"📌 <b>Ваших відстежуваних:</b> {tracked}"
        )
    elif lang == "ru":
        text += (
            f"📊 <b>Всего сигналов:</b> {total}\n"
            f"🟡 <b>Активных:</b> {active}\n"
            f"✅ <b>Выигрышных:</b> {wins}\n"
            f"❌ <b>Проигрышных:</b> {losses}\n"
            f"🏆 <b>Винрейт:</b> {winrate:.1f}%\n\n"
            f"📈 <b>Средний PnL:</b> {avg_pnl:+.2f}%\n"
            f"💪 <b>Средняя уверенность:</b> {avg_conf:.0f}%\n\n"
            f"📌 <b>Ваших отслеживаемых:</b> {tracked}"
        )
    else:
        text += (
            f"📊 <b>Total Signals:</b> {total}\n"
            f"🟡 <b>Active:</b> {active}\n"
            f"✅ <b>Wins:</b> {wins}\n"
            f"❌ <b>Losses:</b> {losses}\n"
            f"🏆 <b>Win Rate:</b> {winrate:.1f}%\n\n"
            f"📈 <b>Avg PnL:</b> {avg_pnl:+.2f}%\n"
            f"💪 <b>Avg Confidence:</b> {avg_conf:.0f}%\n\n"
            f"📌 <b>Your Tracked:</b> {tracked}"
        )

    await answer_callback(callback, text, reply_markup=signals_menu_kb(lang))

def _user_has_access(user: User, signal: Signal) -> bool:
    """Check if user's tier grants access to this signal."""
    tier_levels = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
    user_level = tier_levels.get(user.tier, 0)
    signal_level = tier_levels.get(Tier(signal.min_tier), 0) if signal.min_tier else 0
    return user_level >= signal_level
