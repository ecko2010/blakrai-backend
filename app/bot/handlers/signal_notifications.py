"""
Signal notification handlers — inline button interactions for signal DM delivery.

Handles: View Details, Use Signal, Dismiss, and signal update responses.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.models import User, Signal, SignalStatus, SignalDirection, Tier, UserSignalAction
from app.localization.texts import t
from app.bot.keyboards.inline import (
    signal_detail_kb, signal_notification_kb, signals_menu_kb,
)
from app.bot.utils import answer_callback, safe_delete

router = Router()


@router.callback_query(F.data.startswith("sig_detail_"))
async def cb_signal_detail(callback: CallbackQuery, db_user: User, lang: str):
    """Show full signal details with image card."""
    signal_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if not signal:
            await callback.answer(t("signal_not_found", lang), show_alert=True)
            return

        # Check if user already activated
        result = await session.execute(
            select(UserSignalAction).where(
                UserSignalAction.user_id == db_user.id,
                UserSignalAction.signal_id == signal_id,
            )
        )
        already_activated = result.scalar_one_or_none() is not None

    # Check tier access
    tier_levels = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
    user_level = tier_levels.get(db_user.tier, 0)
    signal_level = tier_levels.get(Tier(signal.min_tier), 0) if signal.min_tier else 0

    if user_level < signal_level:
        await callback.answer(t("error.not_subscribed", lang, tier=signal.min_tier), show_alert=True)
        return

    # Build detail text
    entry = signal.entry_price
    sl = signal.stop_loss
    rr = abs(signal.tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

    tp1_pct = f"{(signal.tp1 - entry) / entry * 100:+.2f}%" if signal.direction == SignalDirection.LONG else f"{(entry - signal.tp1) / entry * 100:+.2f}%"
    sl_pct = f"{(sl - entry) / entry * 100:+.2f}%" if signal.direction == SignalDirection.LONG else f"{(entry - sl) / entry * 100:+.2f}%"

    is_elite = db_user.tier == Tier.ELITE
    text_key = "signal_dm_detail_elite" if is_elite else "signal_dm_detail"

    reasoning = ""
    if is_elite:
        reasoning = (signal.ai_reasoning or "")[:300]
        if not reasoning:
            reasoning = "—"

    text = t(
        text_key, lang,
        signal_id=signal.id,
        coin=signal.coin_symbol,
        direction="🟢 LONG" if signal.direction == SignalDirection.LONG else "🔴 SHORT",
        exchange=signal.exchange,
        timeframe=signal.timeframe,
        entry=f"{entry:,.6g}",
        tp1=f"{signal.tp1:,.6g}",
        tp1_pct=tp1_pct,
        tp2=f"{signal.tp2:,.6g}" if signal.tp2 else "—",
        tp3=f"{signal.tp3:,.6g}" if signal.tp3 else "—",
        sl=f"{sl:,.6g}",
        sl_pct=sl_pct,
        rr=f"1:{rr:.1f}",
        confidence=f"{signal.confidence_score:.0f}",
        leverage=signal.leverage_suggested or "—",
        reasoning=reasoning,
    )

    kb = signal_detail_kb(signal.id, lang, already_activated=already_activated)

    await callback.answer()
    try:
        await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # Fallback: if message has no photo, edit text
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data.startswith("sig_use_"))
async def cb_use_signal(callback: CallbackQuery, db_user: User, lang: str):
    """User activates signal — subscribe to TP/SL updates."""
    signal_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        signal = await session.get(Signal, signal_id)
        if not signal or signal.status in (
            SignalStatus.STOPPED, SignalStatus.TP3_HIT,
            SignalStatus.CLOSED, SignalStatus.EXPIRED, SignalStatus.CANCELLED,
        ):
            await callback.answer(t("signal_not_found", lang), show_alert=True)
            return

        # Check tier access
        tier_levels = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
        user_level = tier_levels.get(db_user.tier, 0)
        signal_level = tier_levels.get(Tier(signal.min_tier), 0) if signal.min_tier else 0

        if user_level < signal_level:
            await callback.answer(t("error.not_subscribed", lang, tier=signal.min_tier), show_alert=True)
            return

        # Create activation record
        action = UserSignalAction(
            user_id=db_user.id,
            signal_id=signal_id,
            notification_message_id=callback.message.message_id,
        )
        session.add(action)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await callback.answer(t("signal_already_activated", lang), show_alert=True)
            return

    await callback.answer(t("signal_activated", lang), show_alert=True)

    # Update keyboard to remove "Use Signal" button
    kb = signal_detail_kb(signal_id, lang, already_activated=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass


@router.callback_query(F.data.startswith("sig_dismiss_"))
async def cb_dismiss_signal(callback: CallbackQuery, db_user: User, lang: str):
    """Dismiss signal notification."""
    await callback.answer()
    await safe_delete(callback.message)


@router.callback_query(F.data == "sig_dismiss_free")
async def cb_dismiss_free(callback: CallbackQuery, db_user: User, lang: str):
    """Dismiss free-tier signal or missed-signal notification."""
    await callback.answer()
    await safe_delete(callback.message)


@router.callback_query(F.data.startswith("sig_back_"))
async def cb_signal_back(callback: CallbackQuery, db_user: User, lang: str):
    """Go back from signal detail to notification view."""
    signal_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        signal = await session.get(Signal, signal_id)

    if not signal:
        await callback.answer(t("signal_not_found", lang), show_alert=True)
        return

    direction_text = "🟢 LONG" if signal.direction == SignalDirection.LONG else "🔴 SHORT"
    caption = t(
        "signal_dm_caption", lang,
        coin=signal.coin_symbol,
        direction=direction_text,
        exchange=signal.exchange,
        confidence=f"{signal.confidence_score:.0f}",
    )

    kb = signal_notification_kb(signal.id, lang)

    await callback.answer()
    try:
        await callback.message.edit_caption(caption=caption, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await callback.message.edit_text(caption, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
