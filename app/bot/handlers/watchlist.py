"""
Watchlist handlers — add/remove/view tracked coins.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.models import User, UserWatchlist
from app.localization.texts import t
from app.bot.keyboards.inline import watchlist_menu_kb, main_menu_kb
from app.bot.utils import answer_callback, safe_delete

router = Router()


class WatchlistStates(StatesGroup):
    waiting_coin = State()


@router.callback_query(F.data == "watchlist")
async def cb_watchlist(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    """Show watchlist + swap reply keyboard."""
    await state.clear()
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    from app.bot.keyboards.reply import watchlist_reply_kb
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id

    async with async_session() as session:
        result = await session.execute(
            select(UserWatchlist).where(UserWatchlist.user_id == db_user.id).order_by(UserWatchlist.added_at.desc())
        )
        items = result.scalars().all()

    if not items:
        text = t("watchlist_empty", lang)
        await _send_or_edit(
            chat_id, callback.bot,
            text=text,
            reply_markup=watchlist_menu_kb([], lang),
            reply_kb=watchlist_reply_kb(lang),
        )
        return

    # Fetch prices
    rows = []
    try:
        from app.exchanges.manager import exchange_manager
        for item in items[:20]:
            try:
                best = await exchange_manager.get_best_price(f"{item.coin_symbol}USDT")
                price = (best.get("best_bid", 0) + best.get("best_ask", 0)) / 2 if best.get("best_bid") else 0
                for name in ("binance", "bybit", "okx"):
                    try:
                        ex = exchange_manager.get_exchange(name)
                        ticker = await ex.get_ticker(f"{item.coin_symbol}USDT")
                        change = ticker.price_change_pct_24h if ticker else 0
                        break
                    except Exception:
                        change = 0
                        continue
                rows.append(t("watchlist_row", lang,
                              coin=item.coin_symbol,
                              price=f"{price:,.6g}",
                              change_24h=f"{change:+.2f}"))
            except Exception:
                rows.append(f"• <b>{item.coin_symbol}</b> — —")
    except Exception:
        rows = [f"• <b>{item.coin_symbol}</b>" for item in items[:20]]

    text = t("watchlist_menu", lang) + "\n\n" + "\n".join(rows)
    await _send_or_edit(
        chat_id, callback.bot,
        text=text,
        reply_markup=watchlist_menu_kb(items, lang),
        reply_kb=watchlist_reply_kb(lang),
    )


@router.callback_query(F.data == "watchlist_add")
async def cb_watchlist_add(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    """Prompt for coin to add."""
    await state.set_state(WatchlistStates.waiting_coin)
    text = t("watchlist_add_prompt", lang)
    await answer_callback(callback, text)


@router.message(WatchlistStates.waiting_coin)
async def msg_watchlist_coin(message: Message, db_user: User, lang: str, state: FSMContext):
    """Receive coin symbol to add to watchlist."""
    await safe_delete(message)
    coin = message.text.strip().upper().replace("USDT", "").replace("/", "")

    if not coin or len(coin) > 20 or not coin.isalpha():
        await message.answer(t("alert_invalid_input", lang), parse_mode="HTML")
        return

    await state.clear()

    async with async_session() as session:
        entry = UserWatchlist(user_id=db_user.id, coin_symbol=coin)
        session.add(entry)
        try:
            await session.commit()
            text = t("watchlist_added", lang, coin=coin)
        except IntegrityError:
            await session.rollback()
            text = t("watchlist_already_exists", lang, coin=coin)

    from app.bot.keyboards.inline import alerts_menu_kb
    await message.answer(text, reply_markup=main_menu_kb(lang), parse_mode="HTML")


@router.callback_query(F.data.startswith("wl_remove_"))
async def cb_watchlist_remove(callback: CallbackQuery, db_user: User, lang: str):
    """Remove coin from watchlist."""
    coin = callback.data.replace("wl_remove_", "").upper()
    async with async_session() as session:
        await session.execute(
            delete(UserWatchlist).where(
                UserWatchlist.user_id == db_user.id,
                UserWatchlist.coin_symbol == coin,
            )
        )
        await session.commit()

    text = t("watchlist_removed", lang, coin=coin)
    await answer_callback(callback, text, reply_markup=main_menu_kb(lang))
