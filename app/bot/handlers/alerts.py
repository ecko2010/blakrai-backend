"""
Alert handlers — create, view, manage, delete user alerts.
Uses FSM for multi-step alert creation flow.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, and_

from app.database import async_session
from app.models import User, UserAlert, AlertType, Tier
from app.localization.texts import t
from app.bot.keyboards.inline import (
    alerts_menu_kb, alert_type_kb, alert_detail_kb, alert_list_kb,
    main_menu_kb,
)
from app.bot.utils import answer_callback, safe_delete
from app.alerts.engine import ALERT_LIMITS, ALERT_TYPES_BY_TIER

router = Router()


# ─── FSM States ──────────────────────────────────────────

class CreateAlertStates(StatesGroup):
    waiting_coin = State()
    waiting_type = State()
    waiting_param = State()


# ─── Alert Type → required param info ───────────────────

PARAM_INPUT_MAP = {
    AlertType.PRICE_ABOVE: "price",
    AlertType.PRICE_BELOW: "price",
    AlertType.CHANGE_1H: "percent",
    AlertType.CHANGE_24H: "percent",
    AlertType.VOLUME_SPIKE: "percent",
    AlertType.RSI_OVERBOUGHT: "rsi",
    AlertType.RSI_OVERSOLD: "rsi",
    AlertType.BB_BREAKOUT: None,  # no param needed
    AlertType.MACD_CROSS: None,
    AlertType.NEW_ATH: None,
    AlertType.NEW_ATL: None,
    AlertType.FUNDING_RATE: "funding",
    AlertType.CORRELATION_BREAK: None,
    AlertType.SUPPORT_HIT: "price",
    AlertType.RESISTANCE_HIT: "price",
    AlertType.CUSTOM_RANGE: "range",
}


# ─── Helpers ─────────────────────────────────────────────

def _format_params(alert_type: AlertType, params: dict) -> str:
    """Format alert params for display."""
    if alert_type in (AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW,
                      AlertType.SUPPORT_HIT, AlertType.RESISTANCE_HIT):
        return f"${params.get('price', 0):,.6g}"
    elif alert_type in (AlertType.CHANGE_1H, AlertType.CHANGE_24H):
        return f"±{params.get('percent', 0)}%"
    elif alert_type == AlertType.VOLUME_SPIKE:
        return f"x{params.get('multiplier', 2)}"
    elif alert_type in (AlertType.RSI_OVERBOUGHT, AlertType.RSI_OVERSOLD):
        return f"RSI {params.get('level', 70)}"
    elif alert_type == AlertType.FUNDING_RATE:
        return f"±{params.get('threshold', 0.1)}%"
    elif alert_type == AlertType.CUSTOM_RANGE:
        return f"${params.get('low', 0):,.6g} — ${params.get('high', 0):,.6g}"
    return ""


async def _get_user_alert_count(user_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(UserAlert.id)).where(
                and_(UserAlert.user_id == user_id, UserAlert.is_active == True)
            )
        )
        return result.scalar() or 0


# ─── Menu Entry ──────────────────────────────────────────

@router.callback_query(F.data == "alerts")
async def cb_alerts_menu(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    """Show alerts menu + swap reply keyboard."""
    await state.clear()
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    from app.bot.keyboards.reply import alerts_reply_kb
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    active = await _get_user_alert_count(db_user.id)
    limit = ALERT_LIMITS.get(db_user.tier, 1)
    text = t("alerts_menu", lang, active=active, limit=limit)
    await _send_or_edit(
        chat_id, callback.bot,
        text=text,
        reply_markup=alerts_menu_kb(lang),
        reply_kb=alerts_reply_kb(lang),
    )


# ─── List My Alerts ─────────────────────────────────────

@router.callback_query(F.data == "my_alerts")
async def cb_my_alerts(callback: CallbackQuery, db_user: User, lang: str):
    """Show user's alert list."""
    async with async_session() as session:
        result = await session.execute(
            select(UserAlert).where(UserAlert.user_id == db_user.id).order_by(UserAlert.created_at.desc()).limit(20)
        )
        alerts = result.scalars().all()

    if not alerts:
        text = t("alerts_empty", lang)
        await answer_callback(callback, text, reply_markup=alerts_menu_kb(lang))
        return

    text = t("alerts_list_header", lang) + "\n"
    for a in alerts:
        status = "🟢" if a.is_active else ("✅" if a.is_triggered else "⏸")
        type_name = t(f"alert.type_{a.alert_type.value}", lang)
        params_str = _format_params(a.alert_type, a.params or {})
        text += f"\n{status} <b>{a.coin_symbol}</b> — {type_name} {params_str}"

    await answer_callback(callback, text, reply_markup=alert_list_kb(alerts, lang))


# ─── Alert Detail ───────────────────────────────────────

@router.callback_query(F.data.startswith("alert_view_"))
async def cb_alert_detail(callback: CallbackQuery, db_user: User, lang: str):
    """View single alert detail."""
    alert_id = int(callback.data.replace("alert_view_", ""))
    async with async_session() as session:
        result = await session.execute(
            select(UserAlert).where(
                and_(UserAlert.id == alert_id, UserAlert.user_id == db_user.id)
            )
        )
        alert = result.scalar_one_or_none()

    if not alert:
        await callback.answer("Not found")
        return

    type_name = t(f"alert.type_{alert.alert_type.value}", lang)
    params_str = _format_params(alert.alert_type, alert.params or {})
    if alert.is_active:
        status = t("alert_status_active", lang)
    elif alert.is_triggered:
        status = t("alert_status_triggered", lang)
    else:
        status = t("alert_status_paused", lang)

    text = t("alert_detail", lang,
             alert_id=alert.id,
             coin=alert.coin_symbol,
             type_name=type_name,
             params_str=params_str,
             status=status,
             triggered_count=alert.triggered_count,
             cooldown=alert.cooldown_minutes)

    await answer_callback(callback, text, reply_markup=alert_detail_kb(alert.id, alert.is_active, lang))


# ─── Toggle Alert ───────────────────────────────────────

@router.callback_query(F.data.startswith("alert_toggle_"))
async def cb_toggle_alert(callback: CallbackQuery, db_user: User, lang: str):
    """Pause/resume an alert."""
    alert_id = int(callback.data.replace("alert_toggle_", ""))
    async with async_session() as session:
        result = await session.execute(
            select(UserAlert).where(
                and_(UserAlert.id == alert_id, UserAlert.user_id == db_user.id)
            )
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_active = not alert.is_active
            session.add(alert)
            await session.commit()

    # Refresh detail
    callback.data = f"alert_view_{alert_id}"
    await cb_alert_detail(callback, db_user, lang)


# ─── Delete Alert ───────────────────────────────────────

@router.callback_query(F.data.startswith("alert_delete_"))
async def cb_delete_alert(callback: CallbackQuery, db_user: User, lang: str):
    """Delete an alert."""
    alert_id = int(callback.data.replace("alert_delete_", ""))
    async with async_session() as session:
        result = await session.execute(
            select(UserAlert).where(
                and_(UserAlert.id == alert_id, UserAlert.user_id == db_user.id)
            )
        )
        alert = result.scalar_one_or_none()
        if alert:
            await session.delete(alert)
            await session.commit()

    text = t("alert_deleted", lang)
    await answer_callback(callback, text, reply_markup=alerts_menu_kb(lang))


# ─── Create Alert Flow ─────────────────────────────────

@router.callback_query(F.data == "create_alert")
async def cb_create_alert_start(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    """Start alert creation — check limits first."""
    active = await _get_user_alert_count(db_user.id)
    limit = ALERT_LIMITS.get(db_user.tier, 1)

    if active >= limit:
        text = t("alert_limit_reached", lang, limit=limit)
        await answer_callback(callback, text, reply_markup=alerts_menu_kb(lang))
        return

    await state.set_state(CreateAlertStates.waiting_coin)
    text = t("alert_choose_coin", lang)
    await answer_callback(callback, text)


@router.message(CreateAlertStates.waiting_coin)
async def msg_alert_coin(message: Message, db_user: User, lang: str, state: FSMContext):
    """Receive coin symbol."""
    await safe_delete(message)
    coin = message.text.strip().upper().replace("USDT", "").replace("/", "")

    if not coin or len(coin) > 20 or not coin.isalpha():
        await message.answer(t("alert_invalid_input", lang), parse_mode="HTML")
        return

    # Validate coin exists on exchange
    try:
        from app.exchanges.manager import exchange_manager
        best = await exchange_manager.get_best_price(f"{coin}USDT")
        if best.get("best_bid") is None:
            await message.answer(t("alert_coin_not_found", lang, coin=coin), parse_mode="HTML")
            return
    except Exception:
        pass  # Allow creation even if exchange check fails

    await state.update_data(coin=coin)
    await state.set_state(CreateAlertStates.waiting_type)

    text = t("alert_choose_type", lang, coin=coin)
    await message.answer(text, reply_markup=alert_type_kb(db_user.tier, lang), parse_mode="HTML")


@router.callback_query(F.data.startswith("atype_"), CreateAlertStates.waiting_type)
async def cb_alert_type_selected(callback: CallbackQuery, db_user: User, lang: str, state: FSMContext):
    """Alert type selected."""
    type_val = callback.data.replace("atype_", "")
    try:
        alert_type = AlertType(type_val)
    except ValueError:
        await callback.answer("Invalid type")
        return

    # Check tier access
    allowed = ALERT_TYPES_BY_TIER.get(db_user.tier, set())
    if alert_type not in allowed:
        required = "Elite" if alert_type not in ALERT_TYPES_BY_TIER.get(Tier.PRO, set()) else "Pro"
        text = t("alert_type_locked", lang, tier=required)
        await answer_callback(callback, text, reply_markup=alerts_menu_kb(lang))
        await state.clear()
        return

    await state.update_data(alert_type=type_val)

    param_kind = PARAM_INPUT_MAP.get(alert_type)

    if param_kind is None:
        # No parameter needed — create immediately
        data = await state.get_data()
        await _create_alert(callback, db_user, lang, state, data["coin"], alert_type, {})
        return

    # Ask for parameter
    prompt_map = {
        "price": "alert_enter_price",
        "percent": "alert_enter_percent",
        "range": "alert_enter_range",
        "rsi": "alert_enter_rsi",
        "funding": "alert_enter_funding",
    }
    await state.set_state(CreateAlertStates.waiting_param)
    await state.update_data(param_kind=param_kind)
    text = t(prompt_map.get(param_kind, "alert_enter_price"), lang)
    await answer_callback(callback, text)


@router.message(CreateAlertStates.waiting_param)
async def msg_alert_param(message: Message, db_user: User, lang: str, state: FSMContext):
    """Receive alert parameter value."""
    await safe_delete(message)
    data = await state.get_data()
    coin = data["coin"]
    alert_type = AlertType(data["alert_type"])
    param_kind = data.get("param_kind", "price")
    text_input = message.text.strip()

    params = {}
    try:
        if param_kind == "price":
            price = float(text_input.replace(",", "").replace("$", ""))
            if price <= 0:
                raise ValueError
            params = {"price": price}

        elif param_kind == "percent":
            pct = float(text_input.replace("%", ""))
            if pct <= 0:
                raise ValueError
            if alert_type == AlertType.VOLUME_SPIKE:
                params = {"multiplier": pct}
            else:
                params = {"percent": pct}

        elif param_kind == "rsi":
            level = float(text_input)
            if not 1 <= level <= 99:
                raise ValueError
            params = {"level": level}

        elif param_kind == "funding":
            threshold = float(text_input.replace("%", ""))
            if threshold <= 0:
                raise ValueError
            params = {"threshold": threshold}

        elif param_kind == "range":
            parts = text_input.split()
            if len(parts) != 2:
                raise ValueError
            low, high = float(parts[0].replace(",", "")), float(parts[1].replace(",", ""))
            if low >= high or low < 0:
                raise ValueError
            params = {"low": low, "high": high}

    except (ValueError, IndexError):
        await message.answer(t("alert_invalid_input", lang), parse_mode="HTML")
        return

    await _create_alert(message, db_user, lang, state, coin, alert_type, params)


async def _create_alert(source, db_user: User, lang: str, state: FSMContext,
                        coin: str, alert_type: AlertType, params: dict):
    """Actually create the alert in DB."""
    async with async_session() as session:
        alert = UserAlert(
            user_id=db_user.id,
            coin_symbol=coin,
            alert_type=alert_type,
            params=params,
            cooldown_minutes=60 if db_user.tier == Tier.FREE else 30,
        )
        session.add(alert)
        await session.commit()

    await state.clear()

    type_name = t(f"alert.type_{alert_type.value}", lang)
    params_str = _format_params(alert_type, params)
    text = t("alert_created", lang, coin=coin, type_name=type_name, params_str=params_str)

    if isinstance(source, CallbackQuery):
        await answer_callback(source, text, reply_markup=alerts_menu_kb(lang))
    else:
        await source.answer(text, reply_markup=alerts_menu_kb(lang), parse_mode="HTML")
