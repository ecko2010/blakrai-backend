"""
Stats handler — statistics display, heatmap generation.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from loguru import logger

from app.models import User
from app.localization.texts import t
from app.stats.calculator import compute_stats
from app.bot.keyboards.inline import stats_menu_kb, signals_menu_kb
from app.bot.utils import answer_callback, safe_delete

router = Router()


@router.callback_query(F.data == "stats")
async def cb_stats_menu(callback: CallbackQuery, db_user: User, lang: str):
    """Show stats menu (now inside signals section)."""
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    from app.bot.keyboards.reply import signals_reply_kb
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    await _send_or_edit(
        chat_id, callback.bot,
        text=t("stats_menu", lang),
        reply_markup=stats_menu_kb(lang),
        reply_kb=signals_reply_kb(lang),
    )


@router.callback_query(F.data.startswith("stats_"))
async def cb_stats_period(callback: CallbackQuery, db_user: User, lang: str):
    """Show statistics for a given period."""
    period_map = {
        "stats_24h": 1,
        "stats_7d": 7,
        "stats_30d": 30,
        "stats_all": None,
    }
    period_days = period_map.get(callback.data)

    await callback.answer(t("loading", lang))

    try:
        stats = await compute_stats(period_days=period_days)
    except Exception as e:
        logger.error(f"Stats computation error: {e}")
        await answer_callback(callback, t("error_generic", lang), reply_markup=stats_menu_kb(lang))
        return

    text = _format_stats(stats, lang)
    await answer_callback(callback, text, reply_markup=stats_menu_kb(lang))


@router.callback_query(F.data == "heatmap")
async def cb_heatmap(callback: CallbackQuery, db_user: User, lang: str):
    """Generate and send performance heatmap."""
    await callback.answer(t("loading", lang))

    try:
        from app.images.heatmap import generate_performance_heatmap
        from app.stats.reports import generate_weekly_digest
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select, and_
        from app.database import async_session
        from app.models import Signal

        digest = await generate_weekly_digest()
        if not digest.top_signals:
            await callback.message.edit_text(
                t("no_data_for_heatmap", lang),
                reply_markup=stats_menu_kb(lang),
            )
            return

        coins = list(dict.fromkeys(s["coin"] for s in digest.top_signals))[:8]
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        # Build real daily PnLs from DB
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)
        daily_pnls = {}
        async with async_session() as session:
            for coin in coins:
                result = await session.execute(
                    select(Signal).where(
                        and_(
                            Signal.coin_symbol == coin,
                            Signal.created_at >= week_start,
                            Signal.pnl_percent.isnot(None),
                        )
                    )
                )
                sigs = result.scalars().all()
                day_pnl = [0.0] * 7
                for sig in sigs:
                    wd = sig.created_at.weekday()  # Mon=0..Sun=6
                    day_pnl[wd] += sig.pnl_percent or 0
                daily_pnls[coin] = day_pnl

        img_bytes = await generate_performance_heatmap(coins, daily_pnls, days)
        photo = BufferedInputFile(img_bytes, filename="heatmap.png")

        # Delete old text message before sending photo
        await safe_delete(callback.message)
        await callback.message.answer_photo(
            photo=photo,
            caption=t("heatmap_caption", lang),
            reply_markup=stats_menu_kb(lang),
        )
    except Exception as e:
        logger.error(f"Heatmap generation error: {e}")
        await answer_callback(callback, t("error_generic", lang), reply_markup=stats_menu_kb(lang))


def _format_stats(stats, lang: str) -> str:
    """Format stats into a nice HTML message."""
    text = f"📊 <b>{stats.period}</b>\n\n"

    text += f"📈 {t('total_signals', lang)}: <b>{stats.total}</b>\n"
    text += f"✅ {t('wins', lang)}: <b>{stats.wins}</b>\n"
    text += f"❌ {t('losses', lang)}: <b>{stats.losses}</b>\n"
    text += f"⏳ {t('active', lang)}: <b>{stats.active}</b>\n\n"

    text += f"🎯 {t('win_rate', lang)}: <b>{stats.win_rate}%</b>\n"
    text += f"💰 {t('total_pnl', lang)}: <b>{'+' if stats.total_pnl > 0 else ''}{stats.total_pnl}%</b>\n"
    text += f"📊 {t('avg_win', lang)}: <b>+{stats.avg_win}%</b>\n"
    text += f"📉 {t('avg_loss', lang)}: <b>{stats.avg_loss}%</b>\n\n"

    text += f"🎯 {t('tp1_rate', lang)}: <b>{stats.tp1_hit_rate}%</b>\n"
    text += f"🎯 {t('tp2_rate', lang)}: <b>{stats.tp2_hit_rate}%</b>\n"
    text += f"🎯 {t('tp3_rate', lang)}: <b>{stats.tp3_hit_rate}%</b>\n\n"

    text += f"📐 {t('profit_factor', lang)}: <b>{stats.profit_factor}</b>\n"
    text += f"📈 {t('sharpe_ratio', lang)}: <b>{stats.sharpe_ratio}</b>\n"
    text += f"📈 {t('sortino_ratio', lang)}: <b>{stats.sortino_ratio}</b>\n"
    text += f"📉 {t('max_drawdown', lang)}: <b>{stats.max_drawdown}%</b>\n\n"

    text += f"🔥 {t('win_streak', lang)}: <b>{stats.win_streak}</b>\n"
    text += f"❄️ {t('loss_streak', lang)}: <b>{stats.loss_streak}</b>\n"
    text += f"⏱ {t('avg_holding', lang)}: <b>{stats.avg_holding_hours}h</b>\n"

    if stats.longs_count > 0:
        text += f"\n🟢 {t('longs_label', lang)}: {stats.longs_count} ({stats.longs_win_rate}% WR)"
    if stats.shorts_count > 0:
        text += f"\n🔴 {t('shorts_label', lang)}: {stats.shorts_count} ({stats.shorts_win_rate}% WR)"

    return text
