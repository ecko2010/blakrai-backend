"""
Inline keyboards for wallet tracking.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.localization.texts import t


def wallet_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 " + t("btn_my_wallets", lang), callback_data="my_wallets"),
        ],
        [
            InlineKeyboardButton(text="➕ " + t("btn_add_wallet", lang), callback_data="wallet_add"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


def wallet_list_kb(wallets: list, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for w in wallets[:10]:
        label = w.label or w.address[:8] + "..."
        chain = w.chain.value.upper()[:4]
        val = f"${w.total_value_usd:,.0f}" if w.total_value_usd else "—"
        rows.append([
            InlineKeyboardButton(
                text=f"[{chain}] {label} {val}",
                callback_data=f"wallet_view_{w.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="wallet_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wallet_detail_kb(wallet_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 " + t("btn_wallet_portfolio", lang), callback_data=f"wallet_portfolio_{wallet_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 " + t("btn_wallet_txs", lang), callback_data=f"wallet_txs_{wallet_id}"),
        ],
        [
            InlineKeyboardButton(text="🤖 " + t("btn_wallet_analysis", lang), callback_data=f"wallet_analyze_{wallet_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 " + t("btn_wallet_remove", lang), callback_data=f"wallet_remove_{wallet_id}"),
            InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="my_wallets"),
        ],
    ])


def wallet_chain_kb(lang: str) -> InlineKeyboardMarkup:
    """Let user pick chain for ambiguous 0x addresses."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Ethereum", callback_data="wchain_ethereum"),
            InlineKeyboardButton(text="BSC", callback_data="wchain_bsc"),
        ],
        [
            InlineKeyboardButton(text="Arbitrum", callback_data="wchain_arbitrum"),
            InlineKeyboardButton(text="Base", callback_data="wchain_base"),
        ],
        [
            InlineKeyboardButton(text="Polygon", callback_data="wchain_polygon"),
        ],
        [InlineKeyboardButton(text="❌ " + t("btn_cancel", lang), callback_data="wallet_menu")],
    ])


def wallet_back_kb(wallet_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data=f"wallet_view_{wallet_id}")],
    ])
