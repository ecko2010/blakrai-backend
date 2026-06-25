"""
Start handler — /start command, language selection, main menu.
Reply keyboard routing with submenus + message editing (no chat spam).
"""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.database import async_session
from app.models import User, Language
from app.localization.texts import t
from app.bot.keyboards.inline import (
    main_menu_kb, language_kb, signals_menu_kb, stats_menu_kb,
    subscription_kb, settings_kb, alerts_menu_kb,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from app.bot.keyboards.reply import (
    main_reply_kb, signals_reply_kb, wallets_reply_kb,
    subscription_reply_kb, settings_reply_kb, alerts_reply_kb,
    watchlist_reply_kb, get_all_reply_texts,
)
from app.bot.keyboards.wallet import wallet_menu_kb
from app.bot.utils import answer_callback, safe_delete, safe_edit_text

router = Router()

# ─── Per-chat last bot message ID tracking ──────────────
# Stores {chat_id: message_id} so we can EDIT instead of flooding chat
_last_bot_msg: dict[int, int] = {}


async def _send_or_edit(
    chat_id: int,
    bot,
    text: str,
    reply_markup=None,
    reply_kb=None,
    parse_mode: str = "HTML",
) -> Message | None:
    """Edit the last bot message if possible, otherwise send a new one.
    If reply_kb is given, sends a NEW message (required to change ReplyKeyboardMarkup),
    then edits it to attach inline buttons if reply_markup is also provided.
    """
    from aiogram.exceptions import TelegramBadRequest

    if reply_kb is not None:
        # Must send a new message to change the bottom reply keyboard.
        old_msg_id = _last_bot_msg.pop(chat_id, None)
        if old_msg_id:
            try:
                await bot.delete_message(chat_id, old_msg_id)
            except Exception:
                pass
        try:
            new_msg = await bot.send_message(
                chat_id, text, reply_markup=reply_kb, parse_mode=parse_mode,
            )
            _last_bot_msg[chat_id] = new_msg.message_id
            # If inline keyboard also needed, edit to attach it
            if reply_markup is not None:
                try:
                    await bot.edit_message_text(
                        text=text, chat_id=chat_id,
                        message_id=new_msg.message_id,
                        reply_markup=reply_markup, parse_mode=parse_mode,
                    )
                except Exception:
                    pass
            return new_msg
        except Exception:
            return None

    # No reply keyboard change — try to edit existing message
    old_msg_id = _last_bot_msg.get(chat_id)
    if old_msg_id:
        try:
            edited = await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=old_msg_id,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return edited
        except TelegramBadRequest as e:
            err = str(e).lower()
            if "message is not modified" in err:
                return None
        except Exception:
            pass

    # Send new message
    try:
        new_msg = await bot.send_message(
            chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode,
        )
        _last_bot_msg[chat_id] = new_msg.message_id
        return new_msg
    except Exception:
        return None


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, lang: str):
    """Handle /start — show welcome + main menu."""
    await safe_delete(message)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id != db_user.telegram_id and db_user.referred_by is None:
                async with async_session() as session:
                    db_user.referred_by = referrer_id
                    session.add(db_user)
                    await session.commit()
        except (ValueError, TypeError):
            pass

    text = t("start", lang, name=message.from_user.first_name)
    # Send welcome + set reply keyboard + inline menu
    await _send_or_edit(
        message.chat.id, message.bot,
        text=text,
        reply_markup=main_menu_kb(lang),
        reply_kb=main_reply_kb(lang),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, db_user: User, lang: str):
    """Return to main menu — also swap reply keyboard back to main."""
    await callback.answer()
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    await _send_or_edit(
        chat_id, callback.bot,
        text=t("main_menu", lang),
        reply_markup=main_menu_kb(lang),
        reply_kb=main_reply_kb(lang),
    )


@router.callback_query(F.data == "change_lang")
async def cb_change_lang(callback: CallbackQuery, db_user: User, lang: str):
    """Show language selection."""
    await answer_callback(callback, t("choose_language", lang), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang_"))
async def cb_set_lang(callback: CallbackQuery, db_user: User, lang: str):
    """Set user language."""
    new_lang = callback.data.replace("lang_", "")
    if new_lang not in ("uk", "en", "ru"):
        await callback.answer("Invalid language")
        return

    async with async_session() as session:
        db_user.language = Language(new_lang)
        session.add(db_user)
        await session.commit()

    from app.bot.middlewares.auth import AuthMiddleware
    await AuthMiddleware.invalidate_user_cache(db_user.telegram_id)

    lang = new_lang
    # Refresh reply keyboard for new language
    await callback.answer()
    _last_bot_msg[callback.message.chat.id] = callback.message.message_id
    await _send_or_edit(
        callback.message.chat.id, callback.bot,
        text=t("language_changed", lang),
        reply_markup=main_menu_kb(lang),
        reply_kb=main_reply_kb(lang),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, db_user: User, lang: str):
    """Show main menu."""
    await safe_delete(message)
    await _send_or_edit(
        message.chat.id, message.bot,
        text=t("main_menu", lang),
        reply_markup=main_menu_kb(lang),
        reply_kb=main_reply_kb(lang),
    )


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery, db_user: User, lang: str):
    """Show help text."""
    await answer_callback(callback, t("help", lang), reply_markup=main_menu_kb(lang))


# ─── Reply Keyboard routing with submenus ────────────────

_REPLY_TEXTS: set[str] = set()
for _l in ("uk", "en", "ru"):
    _REPLY_TEXTS.update(get_all_reply_texts(_l).keys())


def _is_reply_button(message: Message) -> bool:
    """Filter: only match known reply keyboard button texts."""
    return bool(message.text and message.text.strip() in _REPLY_TEXTS)


@router.message(_is_reply_button)
async def reply_keyboard_router(message: Message, db_user: User, lang: str, state: FSMContext):
    """Route reply keyboard presses to submenus. Edits last bot message instead of spamming."""
    text = message.text.strip()
    mapping = get_all_reply_texts(lang)

    callback_data = mapping.get(text)
    if not callback_data:
        for check_lang in ("uk", "en", "ru"):
            m = get_all_reply_texts(check_lang)
            if text in m:
                callback_data = m[text]
                break

    if not callback_data:
        return

    await safe_delete(message)
    bot = message.bot
    chat_id = message.chat.id

    # ─── MAIN MENU sections → open submenu ───────────────────

    if callback_data == "signals":
        await _send_or_edit(
            chat_id, bot,
            text=t("signals_menu", lang),
            reply_markup=signals_menu_kb(lang),
            reply_kb=signals_reply_kb(lang),
        )

    elif callback_data == "wallet_menu":
        from app.wallet.tracker import wallet_tracker, WALLET_LIMITS
        limit = WALLET_LIMITS.get(db_user.tier, 1)
        wallets = await wallet_tracker.get_user_wallets(db_user.id)
        await _send_or_edit(
            chat_id, bot,
            text=t("wallet_menu", lang, count=len(wallets), limit=limit),
            reply_markup=wallet_menu_kb(lang),
            reply_kb=wallets_reply_kb(lang),
        )

    elif callback_data == "subscription":
        await _send_or_edit(
            chat_id, bot,
            text=t("subscription_info", lang),
            reply_markup=subscription_kb(lang),
            reply_kb=subscription_reply_kb(lang),
        )

    elif callback_data == "settings":
        tier_name = {"free": "Free", "pro": "Pro", "elite": "Elite"}.get(
            db_user.tier.value, "Free"
        ) if db_user.tier else "Free"
        await _send_or_edit(
            chat_id, bot,
            text=t("settings", lang, tier=tier_name),
            reply_markup=settings_kb(lang),
            reply_kb=settings_reply_kb(lang),
        )

    elif callback_data == "help":
        await _send_or_edit(
            chat_id, bot,
            text=t("help", lang),
            reply_markup=main_menu_kb(lang),
        )

    # ─── Alerts submenu ──────────────────────────────────────

    elif callback_data == "alerts":
        from app.alerts.engine import ALERT_LIMITS
        from app.models import UserAlert
        async with async_session() as session:
            result = await session.execute(
                select(UserAlert).where(UserAlert.user_id == db_user.id, UserAlert.is_active == True)
            )
            active = len(result.scalars().all())
        limit = ALERT_LIMITS.get(db_user.tier, 1)
        await _send_or_edit(
            chat_id, bot,
            text=t("alerts_menu", lang, active=active, limit=limit),
            reply_markup=alerts_menu_kb(lang),
            reply_kb=alerts_reply_kb(lang),
        )

    elif callback_data == "create_alert":
        from app.bot.handlers.alerts import CreateAlertStates
        from app.alerts.engine import ALERT_LIMITS
        from app.models import UserAlert
        async with async_session() as session:
            result = await session.execute(
                select(UserAlert).where(UserAlert.user_id == db_user.id, UserAlert.is_active == True)
            )
            active = len(result.scalars().all())
        limit = ALERT_LIMITS.get(db_user.tier, 1)
        if active >= limit:
            await _send_or_edit(chat_id, bot, text=t("alert_limit_reached", lang, limit=limit), reply_markup=alerts_menu_kb(lang))
        else:
            await state.set_state(CreateAlertStates.waiting_coin)
            await _send_or_edit(chat_id, bot, text=t("alert_choose_coin", lang), reply_markup=alerts_menu_kb(lang))

    elif callback_data == "my_alerts":
        from app.models import UserAlert
        from app.bot.keyboards.inline import alert_list_kb
        async with async_session() as session:
            result = await session.execute(
                select(UserAlert).where(UserAlert.user_id == db_user.id)
                .order_by(UserAlert.created_at.desc()).limit(20)
            )
            alerts_list = result.scalars().all()
        if not alerts_list:
            await _send_or_edit(chat_id, bot, text=t("alerts_empty", lang), reply_markup=alerts_menu_kb(lang))
        else:
            body = t("alerts_list_header", lang) + "\n"
            for a in alerts_list:
                status = "🟢" if a.is_active else ("✅" if a.is_triggered else "⏸")
                type_name = t(f"alert.type_{a.alert_type.value}", lang)
                body += f"\n{status} <b>{a.coin_symbol}</b> — {type_name}"
            await _send_or_edit(chat_id, bot, text=body, reply_markup=alert_list_kb(alerts_list, lang))

    # ─── Watchlist submenu ───────────────────────────────────

    elif callback_data == "watchlist":
        from app.models import UserWatchlist
        from app.bot.keyboards.inline import watchlist_menu_kb
        async with async_session() as session:
            result = await session.execute(
                select(UserWatchlist).where(UserWatchlist.user_id == db_user.id)
            )
            items = result.scalars().all()
        text_msg = t("watchlist_empty", lang) if not items else t("watchlist_menu", lang)
        await _send_or_edit(
            chat_id, bot,
            text=text_msg,
            reply_markup=watchlist_menu_kb(items, lang),
            reply_kb=watchlist_reply_kb(lang),
        )

    elif callback_data == "watchlist_add":
        from app.bot.handlers.watchlist import WatchlistStates
        await state.set_state(WatchlistStates.waiting_coin)
        await _send_or_edit(chat_id, bot, text=t("watchlist_add_prompt", lang))

    # ─── BACK → return to main menu ─────────────────────────

    elif callback_data == "rk_back":
        await state.clear()
        await _send_or_edit(
            chat_id, bot,
            text=t("main_menu", lang),
            reply_markup=main_menu_kb(lang),
            reply_kb=main_reply_kb(lang),
        )

    # ─── SUBMENU ACTIONS — signals ───────────────────────────

    elif callback_data == "active_signals":
        from app.models import Signal, SignalStatus, SignalDirection
        async with async_session() as session:
            result = await session.execute(
                select(Signal)
                .where(Signal.status.in_((SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT)))
                .order_by(Signal.created_at.desc())
                .limit(10)
            )
            signals = result.scalars().all()

        if not signals:
            await _send_or_edit(chat_id, bot, text=t("no_active_signals", lang), reply_markup=signals_menu_kb(lang))
        else:
            body = t("active_signals_header", lang) + "\n\n"
            for sig in signals:
                d_e = "🟢" if sig.direction == SignalDirection.LONG else "🔴"
                s_e = "🟡" if sig.status == SignalStatus.ACTIVE else "✅"
                pnl = f" | 📈 +{sig.peak_profit_percent:.1f}%" if sig.peak_profit_percent and sig.peak_profit_percent > 0 else ""
                body += (
                    f"{s_e} {d_e} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()}\n"
                    f"   📍 ${sig.entry_price:,.6g} → 🎯 ${sig.tp1:,.6g}{pnl}\n"
                    f"   💪 {sig.confidence_score:.0f}% | {sig.exchange} | {sig.status.value}\n\n"
                )
            await _send_or_edit(chat_id, bot, text=body, reply_markup=signals_menu_kb(lang))

    elif callback_data == "tracked_signals":
        from app.models import Signal, UserSignalAction, SignalDirection, SignalStatus
        async with async_session() as session:
            result = await session.execute(
                select(Signal)
                .join(UserSignalAction, UserSignalAction.signal_id == Signal.id)
                .where(UserSignalAction.user_id == db_user.id)
                .order_by(Signal.created_at.desc())
                .limit(10)
            )
            signals = result.scalars().all()

        if not signals:
            await _send_or_edit(chat_id, bot, text=t("no_tracked_signals", lang), reply_markup=signals_menu_kb(lang))
        else:
            body = t("tracked_signals_header", lang) + "\n\n"
            for sig in signals:
                d_e = "🟢" if sig.direction == SignalDirection.LONG else "🔴"
                pnl_txt = f"{sig.pnl_percent:+.2f}%" if sig.pnl_percent else "—"
                body += f"{d_e} <b>{sig.coin_symbol}</b> {sig.direction.value.upper()} | {sig.status.value} | {pnl_txt}\n"
            await _send_or_edit(chat_id, bot, text=body, reply_markup=signals_menu_kb(lang))

    elif callback_data == "signal_history":
        from app.models import Signal, SignalStatus, SignalDirection
        async with async_session() as session:
            result = await session.execute(
                select(Signal)
                .where(Signal.status.in_((
                    SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
                    SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED,
                )))
                .order_by(Signal.closed_at.desc())
                .limit(10)
            )
            signals = result.scalars().all()

        if not signals:
            await _send_or_edit(chat_id, bot, text=t("no_signal_history", lang), reply_markup=signals_menu_kb(lang))
        else:
            body = t("signal_history_header", lang) + "\n\n"
            for sig in signals:
                d_e = "🟢" if sig.direction == SignalDirection.LONG else "🔴"
                status_map = {"tp1_hit": "🎯1", "tp2_hit": "🎯2", "tp3_hit": "🎯3", "stopped": "🛑", "closed": "📋", "expired": "⏰"}
                s_e = status_map.get(sig.status.value, "❓")
                pnl_txt = f"{sig.pnl_percent:+.2f}%" if sig.pnl_percent else "—"
                body += f"{s_e} {d_e} <b>{sig.coin_symbol}</b> | {pnl_txt}\n"
            await _send_or_edit(chat_id, bot, text=body, reply_markup=signals_menu_kb(lang))

    elif callback_data == "signal_stats":
        from app.stats.calculator import compute_stats
        try:
            stats = await compute_stats(period_days=30)
            body = (
                f"📊 <b>{t('signal_stats_header', lang)}</b>\n\n"
                f"📈 {t('total', lang)}: {stats.total}\n"
                f"✅ {t('wins', lang)}: {stats.wins}\n"
                f"❌ {t('losses', lang)}: {stats.losses}\n"
                f"📊 Win Rate: {stats.win_rate}%\n"
                f"💰 PnL: {stats.total_pnl:+.2f}%\n"
                f"🏆 {t('best_trade', lang)}: {stats.best_trade:+.2f}%\n"
                f"💀 {t('worst_trade', lang)}: {stats.worst_trade:+.2f}%\n"
            )
        except Exception:
            body = t("error_generic", lang)
        await _send_or_edit(chat_id, bot, text=body, reply_markup=signals_menu_kb(lang))

    # ─── SUBMENU ACTIONS — stats (inside signals) ──────────────

    elif callback_data in ("stats_24h", "stats_7d", "stats_30d", "stats_all"):
        from app.stats.calculator import compute_stats
        period_map = {"stats_24h": 1, "stats_7d": 7, "stats_30d": 30, "stats_all": None}
        try:
            stats = await compute_stats(period_days=period_map[callback_data])
            body = _format_stats_text(stats, lang)
        except Exception:
            body = t("error_generic", lang)
        await _send_or_edit(chat_id, bot, text=body, reply_markup=signals_menu_kb(lang))

    elif callback_data == "heatmap":
        # Heatmap sends a photo — can't edit into existing text message
        try:
            from app.images.heatmap import generate_performance_heatmap
            from app.stats.reports import generate_weekly_digest
            from datetime import datetime, timezone, timedelta
            from app.models import Signal

            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            async with async_session() as session:
                result = await session.execute(
                    select(Signal).where(Signal.created_at >= start)
                )
                signals = result.scalars().all()

            if signals:
                img_data = generate_performance_heatmap(signals)
                from aiogram.types import BufferedInputFile
                photo = BufferedInputFile(img_data, filename="heatmap.png")
                await bot.send_photo(
                    chat_id, photo,
                    caption="🔥 Performance Heatmap (7d)",
                    reply_markup=signals_menu_kb(lang),
                )
            else:
                await _send_or_edit(chat_id, bot, text=t("no_data", lang), reply_markup=signals_menu_kb(lang))
        except Exception:
            await _send_or_edit(chat_id, bot, text=t("error_generic", lang), reply_markup=signals_menu_kb(lang))

    # ─── SUBMENU ACTIONS — wallets ───────────────────────────

    elif callback_data == "my_wallets":
        from app.models import TrackedWallet
        async with async_session() as session:
            result = await session.execute(
                select(TrackedWallet).where(TrackedWallet.user_id == db_user.id)
            )
            wallets = result.scalars().all()

        if not wallets:
            await _send_or_edit(chat_id, bot, text=t("no_wallets", lang), reply_markup=wallet_menu_kb(lang))
        else:
            body = "💼 <b>" + t("my_wallets_header", lang) + "</b>\n\n"
            for w in wallets:
                label = w.label or w.address[:8] + "..."
                body += f"• <b>{label}</b> ({w.chain})\n  <code>{w.address}</code>\n\n"
            await _send_or_edit(chat_id, bot, text=body, reply_markup=wallet_menu_kb(lang))

    elif callback_data == "add_wallet":
        from app.bot.handlers.wallet import WalletStates
        from app.wallet.tracker import wallet_tracker, WALLET_LIMITS
        limit = WALLET_LIMITS.get(db_user.tier, 1)
        user_wallets = await wallet_tracker.get_user_wallets(db_user.id)
        if len(user_wallets) >= limit:
            await _send_or_edit(chat_id, bot, text=t("wallet_limit_reached", lang, limit=limit, tier=db_user.tier.value.upper()), reply_markup=wallet_menu_kb(lang))
        else:
            await state.set_state(WalletStates.waiting_address)
            await _send_or_edit(chat_id, bot, text=t("wallet_enter_address", lang), reply_markup=wallet_menu_kb(lang))

    # ─── SUBMENU ACTIONS — subscription ──────────────────────

    elif callback_data == "sub_pro":
        from app.bot.keyboards.inline import payment_duration_kb
        await _send_or_edit(chat_id, bot, text=t("tier_pro_desc", lang), reply_markup=payment_duration_kb("pro", lang))

    elif callback_data == "sub_elite":
        from app.bot.keyboards.inline import payment_duration_kb
        await _send_or_edit(chat_id, bot, text=t("tier_elite_desc", lang), reply_markup=payment_duration_kb("elite", lang))

    elif callback_data == "my_sub":
        tier_name = db_user.tier.value.capitalize() if db_user.tier else "Free"
        expires = ""
        if db_user.subscription_expires_at:
            expires = f"\n⏰ {t('expires', lang)}: {db_user.subscription_expires_at.strftime('%Y-%m-%d')}"
        await _send_or_edit(
            chat_id, bot,
            text=f"📋 <b>{t('my_subscription', lang)}</b>\n\n🏷 {t('tier', lang)}: <b>{tier_name}</b>{expires}",
            reply_markup=subscription_kb(lang),
        )

    # ─── SUBMENU ACTIONS — settings ──────────────────────────

    elif callback_data == "change_lang":
        await _send_or_edit(chat_id, bot, text=t("choose_language", lang), reply_markup=language_kb())

    elif callback_data == "notifications_settings":
        await _send_or_edit(chat_id, bot, text=t("coming_soon", lang), reply_markup=settings_kb(lang))

    elif callback_data == "api_key_menu":
        from app.bot.keyboards.inline import api_key_menu_kb
        from app.models import UserApiKey
        async with async_session() as session:
            key = await session.scalar(
                select(UserApiKey).where(
                    UserApiKey.user_id == db_user.id,
                    UserApiKey.is_active == True,
                )
            )
        has_key = key is not None
        if has_key:
            body = f"🔑 <b>API Key</b>\n\n<code>{key.key_prefix}...{key.key_suffix}</code>\n{t('api_key_active', lang)}"
        else:
            body = f"🔑 <b>API Key</b>\n\n{t('no_api_key', lang)}"
        await _send_or_edit(chat_id, bot, text=body, reply_markup=api_key_menu_kb(lang, has_key))


def _format_stats_text(stats, lang: str) -> str:
    """Format stats into HTML text for reply keyboard responses."""
    return (
        f"📊 <b>{stats.period}</b>\n\n"
        f"📈 {t('total', lang)}: {stats.total}\n"
        f"✅ {t('wins', lang)}: {stats.wins} | ❌ {t('losses', lang)}: {stats.losses}\n"
        f"📊 Win Rate: <b>{stats.win_rate}%</b>\n"
        f"💰 PnL: <b>{stats.total_pnl:+.2f}%</b>\n"
        f"🏆 {t('best_trade', lang)}: {stats.best_trade:+.2f}%\n"
        f"💀 {t('worst_trade', lang)}: {stats.worst_trade:+.2f}%\n"
        f"📐 Sharpe: {stats.sharpe_ratio} | Sortino: {stats.sortino_ratio}\n"
        f"📉 Max DD: {stats.max_drawdown:.2f}%\n"
    )
