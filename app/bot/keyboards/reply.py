"""
Reply keyboards — persistent bottom menu (ReplyKeyboardMarkup) for quick navigation.
These buttons are always visible under the chat input.
Supports submenus: tapping a section swaps the keyboard to its submenu.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.localization.texts import t


def _rk(key: str, lang: str) -> str:
    return t(key, lang)


# ─── Main menu ────────────────────────────────────────────

def main_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Main persistent keyboard — always visible at the bottom of chat."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_signals", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_alerts", lang)),
                KeyboardButton(text=_rk("rk_watchlist", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_wallets", lang)),
                KeyboardButton(text=_rk("rk_subscription", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_settings", lang)),
                KeyboardButton(text=_rk("rk_help", lang)),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ─── Submenus ─────────────────────────────────────────────

def signals_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Signals submenu keyboard — includes stats & cleanup."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_active_signals", lang)),
                KeyboardButton(text=_rk("rk_tracked_signals", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_signal_history", lang)),
                KeyboardButton(text=_rk("rk_signal_stats", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_stats_24h", lang)),
                KeyboardButton(text=_rk("rk_stats_7d", lang)),
                KeyboardButton(text=_rk("rk_stats_30d", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_stats_all", lang)),
                KeyboardButton(text=_rk("rk_heatmap", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def wallets_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Wallets submenu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_my_wallets", lang)),
                KeyboardButton(text=_rk("rk_add_wallet", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def subscription_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Subscription submenu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_sub_pro", lang)),
                KeyboardButton(text=_rk("rk_sub_elite", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_my_sub", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def settings_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Settings submenu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_language", lang)),
                KeyboardButton(text=_rk("rk_notifications", lang)),
            ],
            [
                KeyboardButton(text=_rk("rk_api_key", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def alerts_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Alerts submenu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_create_alert", lang)),
                KeyboardButton(text=_rk("rk_my_alerts", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def watchlist_reply_kb(lang: str) -> ReplyKeyboardMarkup:
    """Watchlist submenu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=_rk("rk_add_watchlist", lang)),
            ],
            [KeyboardButton(text=_rk("rk_back", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# ─── All reply button texts for matching ─────────────────

def get_all_reply_texts(lang: str) -> dict[str, str]:
    """Return mapping: reply button text -> callback_data equivalent.
    Includes main menu + all submenus + back button.
    """
    return {
        # Main menu
        _rk("rk_signals", lang): "signals",
        _rk("rk_alerts", lang): "alerts",
        _rk("rk_watchlist", lang): "watchlist",
        _rk("rk_wallets", lang): "wallet_menu",
        _rk("rk_subscription", lang): "subscription",
        _rk("rk_settings", lang): "settings",
        _rk("rk_help", lang): "help",
        # Back
        _rk("rk_back", lang): "rk_back",
        # Signals submenu (includes stats)
        _rk("rk_active_signals", lang): "active_signals",
        _rk("rk_tracked_signals", lang): "tracked_signals",
        _rk("rk_signal_history", lang): "signal_history",
        _rk("rk_signal_stats", lang): "signal_stats",
        _rk("rk_stats_24h", lang): "stats_24h",
        _rk("rk_stats_7d", lang): "stats_7d",
        _rk("rk_stats_30d", lang): "stats_30d",
        _rk("rk_stats_all", lang): "stats_all",
        _rk("rk_heatmap", lang): "heatmap",
        # Alerts submenu
        _rk("rk_create_alert", lang): "create_alert",
        _rk("rk_my_alerts", lang): "my_alerts",
        # Watchlist submenu
        _rk("rk_add_watchlist", lang): "watchlist_add",
        # Wallets submenu
        _rk("rk_my_wallets", lang): "my_wallets",
        _rk("rk_add_wallet", lang): "add_wallet",
        # Subscription submenu
        _rk("rk_sub_pro", lang): "sub_pro",
        _rk("rk_sub_elite", lang): "sub_elite",
        _rk("rk_my_sub", lang): "my_sub",
        # Settings submenu
        _rk("rk_language", lang): "change_lang",
        _rk("rk_notifications", lang): "notifications_settings",
        _rk("rk_api_key", lang): "api_key_menu",
    }
