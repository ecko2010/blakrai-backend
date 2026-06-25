"""
Inline keyboards for the Telegram bot.
All keyboards use callbacks, no hardcoded text in buttons — uses localization keys.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.localization.texts import t


# ─── Main Menu (reorganized: signals, stats, alerts, watchlist, sub, settings, help) ─

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_signals", lang), callback_data="signals"),
        ],
        [
            InlineKeyboardButton(text=t("btn_alerts", lang), callback_data="alerts"),
            InlineKeyboardButton(text=t("btn_watchlist", lang), callback_data="watchlist"),
        ],
        [
            InlineKeyboardButton(text=t("btn_wallets", lang), callback_data="wallet_menu"),
            InlineKeyboardButton(text=t("btn_subscription", lang), callback_data="subscription"),
        ],
        [
            InlineKeyboardButton(text=t("btn_settings", lang), callback_data="settings"),
        ],
        [
            InlineKeyboardButton(text=t("btn_help", lang), callback_data="help"),
        ],
    ])


# ─── Language Selection ─────────────────────────────────

def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇪🇬 العربية", callback_data="lang_ar"),
        ],
    ])


# ─── Signals Menu ──────────────────────────────────────

def signals_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_active_signals", lang), callback_data="active_signals"),
            InlineKeyboardButton(text=t("btn_tracked_signals", lang), callback_data="tracked_signals"),
        ],
        [
            InlineKeyboardButton(text=t("btn_signal_history", lang), callback_data="signal_history"),
            InlineKeyboardButton(text=t("btn_signal_stats", lang), callback_data="signal_stats"),
        ],
        [
            InlineKeyboardButton(text="📊 24h", callback_data="stats_24h"),
            InlineKeyboardButton(text="📊 7d", callback_data="stats_7d"),
            InlineKeyboardButton(text="📊 30d", callback_data="stats_30d"),
        ],
        [
            InlineKeyboardButton(text="📊 " + t("btn_all_time", lang), callback_data="stats_all"),
            InlineKeyboardButton(text="🔥 " + t("btn_heatmap", lang), callback_data="heatmap"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


# ─── Stats Menu (now part of signals section) ──────────

def stats_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 24h", callback_data="stats_24h"),
            InlineKeyboardButton(text="📊 7d", callback_data="stats_7d"),
            InlineKeyboardButton(text="📊 30d", callback_data="stats_30d"),
        ],
        [
            InlineKeyboardButton(text="📊 " + t("btn_all_time", lang), callback_data="stats_all"),
        ],
        [
            InlineKeyboardButton(text="🔥 " + t("btn_heatmap", lang), callback_data="heatmap"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="signals")],
    ])


# ─── Subscription ──────────────────────────────────────

def subscription_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ Pro", callback_data="sub_pro"),
            InlineKeyboardButton(text="💎 Elite", callback_data="sub_elite"),
        ],
        [
            InlineKeyboardButton(text=t("btn_my_subscription", lang), callback_data="my_sub"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


def payment_duration_kb(tier: str, lang: str) -> InlineKeyboardMarkup:
    mo = t("month_short", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"1 {mo}", callback_data=f"pay_{tier}_1"),
            InlineKeyboardButton(text=f"3 {mo}", callback_data=f"pay_{tier}_3"),
        ],
        [
            InlineKeyboardButton(text=f"6 {mo} (-10%)", callback_data=f"pay_{tier}_6"),
            InlineKeyboardButton(text=f"12 {mo} (-20%)", callback_data=f"pay_{tier}_12"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="subscription")],
    ])


def payment_confirm_kb(payment_url: str, payment_id: str, lang: str) -> InlineKeyboardMarkup:
    pay_text = "💳 " + (t("btn_pay", lang))
    check_text = "🔄 " + (t("btn_check_payment", lang))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, url=payment_url)],
        [InlineKeyboardButton(text=check_text, callback_data=f"check_pay_{payment_id}")],
        [InlineKeyboardButton(text="❌ " + t("btn_cancel", lang), callback_data="subscription")],
    ])


# ─── Settings ──────────────────────────────────────────

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 " + t("btn_language", lang), callback_data="change_lang"),
        ],
        [
            InlineKeyboardButton(text="🔔 " + t("btn_notifications", lang), callback_data="notifications_settings"),
        ],
        [
            InlineKeyboardButton(text="🔑 " + t("btn_api_key", lang), callback_data="api_key_menu"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


def api_key_menu_kb(lang: str, has_key: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if has_key:
        buttons.append([InlineKeyboardButton(text="🔄 " + t("btn_regenerate_key", lang), callback_data="api_key_generate")])
        buttons.append([InlineKeyboardButton(text="🗑 " + t("btn_revoke_key", lang), callback_data="api_key_revoke")])
    else:
        buttons.append([InlineKeyboardButton(text="🔑 " + t("btn_generate_key", lang), callback_data="api_key_generate")])
    buttons.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Admin ──────────────────────────────────────────────

def admin_kb(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("admin_btn_stats", lang), callback_data="admin_system"),
            InlineKeyboardButton(text=t("admin_btn_users", lang), callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text=t("admin_btn_scan", lang), callback_data="admin_scan"),
            InlineKeyboardButton(text=t("admin_btn_ai", lang), callback_data="admin_ai"),
        ],
        [
            InlineKeyboardButton(text=t("admin_btn_broadcast", lang), callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🗑 Cleanup", callback_data="admin_cleanup"),
        ],
    ])


def admin_cleanup_kb(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Stopped", callback_data="adm_clean_stopped")],
        [InlineKeyboardButton(text="⏰ Expired", callback_data="adm_clean_expired")],
        [InlineKeyboardButton(text="📋 Closed", callback_data="adm_clean_closed")],
        [InlineKeyboardButton(text="🗑 All closed", callback_data="adm_clean_all_old")],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="admin_panel")],
    ])


def admin_cleanup_confirm_kb(action: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"adm_clean_yes_{action}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="admin_cleanup")],
    ])


# ─── Pagination ─────────────────────────────────────────

def pagination_kb(current_page: int, total_pages: int, prefix: str, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_page_{current_page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_page_{current_page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


# ─── Alerts ─────────────────────────────────────────────

def alerts_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_create_alert", lang), callback_data="create_alert"),
        ],
        [
            InlineKeyboardButton(text=t("btn_my_alerts", lang), callback_data="my_alerts"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")],
    ])


def alert_type_kb(tier, lang: str) -> InlineKeyboardMarkup:
    """Keyboard with alert types available for the user's tier."""
    from app.models import AlertType, Tier
    from app.alerts.engine import ALERT_TYPES_BY_TIER

    allowed = ALERT_TYPES_BY_TIER.get(tier, ALERT_TYPES_BY_TIER.get(Tier.FREE, set()))

    # Define display order
    type_order = [
        AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW,
        AlertType.CHANGE_1H, AlertType.CHANGE_24H,
        AlertType.RSI_OVERBOUGHT, AlertType.RSI_OVERSOLD,
        AlertType.BB_BREAKOUT, AlertType.VOLUME_SPIKE,
        AlertType.FUNDING_RATE, AlertType.CUSTOM_RANGE,
        AlertType.SUPPORT_HIT, AlertType.RESISTANCE_HIT,
        AlertType.MACD_CROSS, AlertType.NEW_ATH, AlertType.NEW_ATL,
        AlertType.CORRELATION_BREAK,
    ]

    rows = []
    row = []
    for at in type_order:
        label = t(f"alert.type_{at.value}", lang)
        if at not in allowed:
            label = "🔒 " + label
        row.append(InlineKeyboardButton(text=label, callback_data=f"atype_{at.value}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="alerts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alert_list_kb(alerts: list, lang: str) -> InlineKeyboardMarkup:
    """Keyboard with buttons to view each alert."""
    rows = []
    for a in alerts[:10]:
        type_name = t(f"alert.type_{a.alert_type.value}", lang)
        label = f"{a.coin_symbol} — {type_name}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"alert_view_{a.id}")])
    rows.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="alerts")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def alert_detail_kb(alert_id: int, is_active: bool, lang: str) -> InlineKeyboardMarkup:
    """Keyboard for single alert: toggle, delete, back."""
    toggle_text = "⏸ Pause" if is_active else "▶️ Enable"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"alert_toggle_{alert_id}"),
            InlineKeyboardButton(text=t("btn_delete_alert", lang), callback_data=f"alert_delete_{alert_id}"),
        ],
        [InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="my_alerts")],
    ])


# ─── Watchlist ──────────────────────────────────────────

def watchlist_menu_kb(items: list, lang: str) -> InlineKeyboardMarkup:
    """Watchlist keyboard with add button and remove buttons per coin."""
    rows = []
    rows.append([InlineKeyboardButton(text=t("btn_add_watchlist", lang), callback_data="watchlist_add")])
    for item in items[:10]:
        coin = item.coin_symbol if hasattr(item, "coin_symbol") else str(item)
        rows.append([
            InlineKeyboardButton(text=f"🗑 {coin}", callback_data=f"wl_remove_{coin}"),
        ])
    rows.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Signal Notification Keyboards ──────────────────────

def signal_notification_kb(signal_id: int, lang: str) -> InlineKeyboardMarkup:
    """Keyboard for new signal DM notification: Details | Use Signal | Dismiss."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_view_details", lang), callback_data=f"sig_detail_{signal_id}"),
            InlineKeyboardButton(text=t("btn_use_signal", lang), callback_data=f"sig_use_{signal_id}"),
        ],
        [
            InlineKeyboardButton(text=t("btn_dismiss", lang), callback_data=f"sig_dismiss_{signal_id}"),
        ],
    ])


def signal_notification_free_kb(lang: str) -> InlineKeyboardMarkup:
    """Keyboard for FREE user signal notification: Subscribe CTA."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_subscribe_pro", lang), callback_data="subscription"),
        ],
        [
            InlineKeyboardButton(text=t("btn_dismiss", lang), callback_data="sig_dismiss_free"),
        ],
    ])


def signal_detail_kb(signal_id: int, lang: str, already_activated: bool = False) -> InlineKeyboardMarkup:
    """Keyboard shown on signal detail view."""
    rows = []
    if not already_activated:
        rows.append([InlineKeyboardButton(text=t("btn_use_signal", lang), callback_data=f"sig_use_{signal_id}")])
    rows.append([InlineKeyboardButton(text="◀️ " + t("btn_back", lang), callback_data=f"sig_back_{signal_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def signal_update_kb(signal_id: int, lang: str) -> InlineKeyboardMarkup:
    """Keyboard on signal update notification (TP/SL hit)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_view_signal", lang), callback_data=f"sig_detail_{signal_id}")],
    ])


def missed_signals_kb(lang: str) -> InlineKeyboardMarkup:
    """Keyboard on missed signals reminder."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_view_active", lang), callback_data="active_signals")],
        [InlineKeyboardButton(text=t("btn_dismiss", lang), callback_data="sig_dismiss_free")],
    ])
