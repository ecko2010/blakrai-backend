"""
Wallet tracking handlers — add/remove/view wallets, portfolio, transactions, AI analysis.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from app.database import async_session
from app.models import User, TrackedWallet, ChainType, Tier
from app.localization.texts import t
from app.bot.keyboards.wallet import (
    wallet_menu_kb, wallet_list_kb, wallet_detail_kb,
    wallet_chain_kb, wallet_back_kb,
)
from app.bot.keyboards.inline import main_menu_kb
from app.bot.keyboards.reply import wallets_reply_kb
from app.bot.utils import answer_callback, safe_delete
from app.wallet.tracker import wallet_tracker, WALLET_LIMITS, TIER_FEATURES
from app.wallet.chains import detect_chain, EVM_CHAINS

router = Router()


class WalletStates(StatesGroup):
    waiting_address = State()
    waiting_chain = State()  # For ambiguous 0x addresses
    waiting_label = State()


# ─── Wallet Menu ──────────────────────────────────────

@router.callback_query(F.data == "wallet_menu")
async def cb_wallet_menu(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    await state.clear()
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    limit = WALLET_LIMITS.get(db_user.tier, 1)
    wallets = await wallet_tracker.get_user_wallets(db_user.id)
    text = t("wallet_menu", lang, count=len(wallets), limit=limit)
    await _send_or_edit(
        chat_id, callback.bot,
        text=text,
        reply_markup=wallet_menu_kb(lang),
        reply_kb=wallets_reply_kb(lang),
    )


# ─── My Wallets ──────────────────────────────────────

@router.callback_query(F.data == "my_wallets")
async def cb_my_wallets(callback: CallbackQuery, db_user: User, lang: str):
    wallets = await wallet_tracker.get_user_wallets(db_user.id)
    if not wallets:
        text = t("wallet_empty", lang)
        await answer_callback(callback, text, reply_markup=wallet_menu_kb(lang))
        return

    text = t("wallet_list_header", lang, count=len(wallets))
    await answer_callback(callback, text, reply_markup=wallet_list_kb(wallets, lang))


# ─── Add Wallet ──────────────────────────────────────

@router.callback_query(F.data == "wallet_add")
async def cb_wallet_add(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    limit = WALLET_LIMITS.get(db_user.tier, 1)
    wallets = await wallet_tracker.get_user_wallets(db_user.id)
    if len(wallets) >= limit:
        text = t("wallet_limit_reached", lang, limit=limit, tier=db_user.tier.value.upper())
        await answer_callback(callback, text, reply_markup=wallet_menu_kb(lang))
        return

    await state.set_state(WalletStates.waiting_address)
    text = t("wallet_enter_address", lang)
    await answer_callback(callback, text)


@router.message(WalletStates.waiting_address)
async def msg_wallet_address(message: Message, db_user: User, lang: str, state: FSMContext):
    await safe_delete(message)
    address = message.text.strip()

    if len(address) < 20 or len(address) > 128:
        await message.answer(t("wallet_invalid_address", lang), parse_mode="HTML")
        return

    chain = detect_chain(address)

    if chain is None:
        await state.clear()
        await message.answer(t("wallet_unknown_chain", lang), reply_markup=wallet_menu_kb(lang), parse_mode="HTML")
        return

    # For EVM addresses: ask which chain
    if chain in EVM_CHAINS:
        await state.update_data(address=address)
        await state.set_state(WalletStates.waiting_chain)
        await message.answer(
            t("wallet_select_chain", lang),
            reply_markup=wallet_chain_kb(lang),
            parse_mode="HTML",
        )
        return

    # Non-ambiguous chain (Solana, Tron) — add directly
    await state.update_data(address=address, chain=chain.value)
    await state.set_state(WalletStates.waiting_label)
    await message.answer(t("wallet_enter_label", lang), parse_mode="HTML")


@router.callback_query(F.data.startswith("wchain_"), WalletStates.waiting_chain)
async def cb_wallet_chain(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    chain_str = callback.data.replace("wchain_", "")
    try:
        chain = ChainType(chain_str)
    except ValueError:
        await answer_callback(callback, t("wallet_invalid_chain", lang), reply_markup=wallet_menu_kb(lang))
        await state.clear()
        return

    await state.update_data(chain=chain.value)
    await state.set_state(WalletStates.waiting_label)
    await answer_callback(callback, t("wallet_enter_label", lang))


@router.message(WalletStates.waiting_label)
async def msg_wallet_label(message: Message, db_user: User, lang: str, state: FSMContext):
    await safe_delete(message)
    data = await state.get_data()
    address = data.get("address", "")
    chain_str = data.get("chain", "")
    label = message.text.strip()[:100] if message.text.strip() != "-" else None

    await state.clear()

    try:
        chain = ChainType(chain_str)
    except ValueError:
        await message.answer(t("wallet_error", lang), reply_markup=wallet_menu_kb(lang), parse_mode="HTML")
        return

    result = await wallet_tracker.add_wallet(db_user.id, address, chain, label)

    if isinstance(result, str):
        # Error string
        error_key = f"wallet_err_{result}"
        await message.answer(t(error_key, lang), reply_markup=wallet_menu_kb(lang), parse_mode="HTML")
        return

    # Success
    chain_label = chain.value.upper()
    wallet_label = label or address[:12] + "..."
    text = t("wallet_added", lang, label=wallet_label, chain=chain_label)
    await message.answer(text, reply_markup=wallet_menu_kb(lang), parse_mode="HTML")


# ─── View Wallet ──────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_view_"))
async def cb_wallet_view(callback: CallbackQuery, db_user: User, lang: str):
    wallet_id = int(callback.data.replace("wallet_view_", ""))

    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != db_user.id:
            await answer_callback(callback, t("wallet_not_found", lang), reply_markup=wallet_menu_kb(lang))
            return

    label = wallet.label or wallet.address[:12] + "..."
    chain = wallet.chain.value.upper()
    val = f"${wallet.total_value_usd:,.2f}" if wallet.total_value_usd else "—"
    native = f"{wallet.native_balance:,.6g}" if wallet.native_balance else "—"
    scanned = wallet.last_scanned_at.strftime("%d.%m %H:%M") if wallet.last_scanned_at else "—"

    text = (
        f"🏦 <b>{label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Мережа: {chain}\n"
        f"📍 Адреса: <code>{wallet.address}</code>\n\n"
        f"💰 Загальна вартість: <b>{val}</b>\n"
        f"🪙 Нативний баланс: {native}\n"
        f"🕐 Останнє сканування: {scanned}"
    )

    await answer_callback(callback, text, reply_markup=wallet_detail_kb(wallet_id, lang))


# ─── Portfolio ────────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_portfolio_"))
async def cb_wallet_portfolio(callback: CallbackQuery, db_user: User, lang: str):
    wallet_id = int(callback.data.replace("wallet_portfolio_", ""))
    portfolio = await wallet_tracker.get_wallet_portfolio(wallet_id)

    if not portfolio or portfolio.get("wallet", {}) == {}:
        await answer_callback(callback, t("wallet_not_found", lang), reply_markup=wallet_menu_kb(lang))
        return

    wallet = portfolio["wallet"]
    if wallet.user_id != db_user.id:
        await answer_callback(callback, t("wallet_not_found", lang), reply_markup=wallet_menu_kb(lang))
        return

    tokens = portfolio["tokens"]
    total = portfolio["total_value_usd"]

    if not tokens:
        text = t("wallet_portfolio_empty", lang)
        await answer_callback(callback, text, reply_markup=wallet_back_kb(wallet_id, lang))
        return

    lines = [f"📊 <b>Портфель</b> — ${total:,.2f}\n"]
    for tok in tokens[:15]:
        pct = ((tok.value_usd / total) * 100) if total and tok.value_usd else 0
        val_str = f"${tok.value_usd:,.2f}" if tok.value_usd else "—"
        bar = "█" * max(1, int(pct / 5)) if pct > 0 else "░"
        lines.append(f"• <b>{tok.symbol}</b>: {tok.balance:,.6g} ({val_str}, {pct:.1f}%)\n  {bar}")

    if len(tokens) > 15:
        lines.append(f"\n... ще {len(tokens) - 15} токенів")

    text = "\n".join(lines)
    await answer_callback(callback, text, reply_markup=wallet_back_kb(wallet_id, lang))


# ─── Transactions ─────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_txs_"))
async def cb_wallet_txs(callback: CallbackQuery, db_user: User, lang: str):
    wallet_id = int(callback.data.replace("wallet_txs_", ""))

    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != db_user.id:
            await answer_callback(callback, t("wallet_not_found", lang), reply_markup=wallet_menu_kb(lang))
            return

    # Check tier
    if "tx_alerts" not in TIER_FEATURES.get(db_user.tier, set()):
        await answer_callback(callback, t("wallet_pro_required", lang), reply_markup=wallet_back_kb(wallet_id, lang))
        return

    txs = await wallet_tracker.get_wallet_transactions(wallet_id, limit=10)

    if not txs:
        text = t("wallet_no_txs", lang)
        await answer_callback(callback, text, reply_markup=wallet_back_kb(wallet_id, lang))
        return

    lines = ["📝 <b>Останні транзакції</b>\n"]
    for tx in txs:
        emoji = {"receive": "📥", "transfer": "📤", "swap": "🔄", "approve": "✅"}.get(tx.tx_type, "📝")
        date_str = tx.timestamp.strftime("%d.%m %H:%M") if tx.timestamp else "—"
        amount_str = f"{tx.amount:,.6g} {tx.token_symbol}" if tx.amount and tx.token_symbol else "—"
        usd_str = f" (${tx.amount_usd:,.2f})" if tx.amount_usd else ""
        hash_short = tx.tx_hash[:10] + "..."

        lines.append(f"{emoji} {date_str} | {amount_str}{usd_str}\n   <code>{hash_short}</code>")

    text = "\n".join(lines)
    await answer_callback(callback, text, reply_markup=wallet_back_kb(wallet_id, lang))


# ─── AI Analysis ──────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_analyze_"))
async def cb_wallet_analyze(callback: CallbackQuery, db_user: User, lang: str):
    wallet_id = int(callback.data.replace("wallet_analyze_", ""))

    async with async_session() as session:
        wallet = await session.get(TrackedWallet, wallet_id)
        if not wallet or wallet.user_id != db_user.id:
            await answer_callback(callback, t("wallet_not_found", lang), reply_markup=wallet_menu_kb(lang))
            return

    # Check tier
    if "analytics" not in TIER_FEATURES.get(db_user.tier, set()):
        await answer_callback(callback, t("wallet_pro_required", lang), reply_markup=wallet_back_kb(wallet_id, lang))
        return

    await callback.answer(t("wallet_analyzing", lang), show_alert=False)

    from app.wallet.analytics import generate_portfolio_analysis
    analysis = await generate_portfolio_analysis(wallet_id)

    if not analysis:
        text = t("wallet_analysis_failed", lang)
    else:
        text = f"🤖 <b>AI Аналітика портфелю</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{analysis}"

    await answer_callback(callback, text, reply_markup=wallet_back_kb(wallet_id, lang))


# ─── Remove Wallet ────────────────────────────────────

@router.callback_query(F.data.startswith("wallet_remove_"))
async def cb_wallet_remove(callback: CallbackQuery, db_user: User, lang: str):
    wallet_id = int(callback.data.replace("wallet_remove_", ""))

    success = await wallet_tracker.remove_wallet(db_user.id, wallet_id)
    if success:
        text = t("wallet_removed", lang)
    else:
        text = t("wallet_not_found", lang)

    await answer_callback(callback, text, reply_markup=wallet_menu_kb(lang))
