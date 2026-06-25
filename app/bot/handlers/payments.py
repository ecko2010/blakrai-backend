"""
Payment handler — NOWPayments integration, subscription purchase flow.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from app.models import User, Tier
from app.localization.texts import t
from app.bot.keyboards.inline import (
    subscription_kb, payment_duration_kb, payment_confirm_kb, main_menu_kb,
)
from app.payments.nowpayments import nowpayments_client
from app.bot.keyboards.reply import subscription_reply_kb
from app.bot.utils import answer_callback, safe_delete

router = Router()


@router.callback_query(F.data == "subscription")
async def cb_subscription(callback: CallbackQuery, db_user: User, lang: str):
    """Show subscription options + swap reply keyboard."""
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    text = t("subscription_info", lang, current_tier=db_user.tier.value.capitalize())
    await _send_or_edit(
        chat_id, callback.bot,
        text=text,
        reply_markup=subscription_kb(lang),
        reply_kb=subscription_reply_kb(lang),
    )


@router.callback_query(F.data.in_({"sub_pro", "sub_elite"}))
async def cb_select_tier(callback: CallbackQuery, db_user: User, lang: str):
    """Select subscription tier, show duration options."""
    tier = "pro" if callback.data == "sub_pro" else "elite"
    text = t(f"tier_{tier}_desc", lang)
    await answer_callback(callback, text, reply_markup=payment_duration_kb(tier, lang))


@router.callback_query(F.data.startswith("pay_"))
async def cb_create_payment(callback: CallbackQuery, db_user: User, lang: str):
    """Create payment via NOWPayments."""
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Invalid")
        return

    tier = parts[1]
    months = int(parts[2])

    await callback.answer(t("loading", lang))

    try:
        payment = await nowpayments_client.create_payment(
            user=db_user,
            tier=Tier.PRO if tier == "pro" else Tier.ELITE,
            months=months,
        )

        if payment:
            text = t("payment_created", lang, amount=payment["amount_usd"], currency="USD")
            await answer_callback(
                callback, text,
                reply_markup=payment_confirm_kb(
                    payment_url=payment["invoice_url"],
                    payment_id=str(payment["payment_id"]),
                    lang=lang,
                ),
            )
        else:
            await answer_callback(callback, t("payment_error", lang), reply_markup=subscription_kb(lang))
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await answer_callback(callback, t("payment_error", lang), reply_markup=subscription_kb(lang))


@router.callback_query(F.data.startswith("check_pay_"))
async def cb_check_payment(callback: CallbackQuery, db_user: User, lang: str):
    """Check payment status."""
    payment_id = callback.data.replace("check_pay_", "")

    try:
        status = await nowpayments_client.check_payment_status(payment_id)

        if status == "finished":
            await answer_callback(callback, t("payment_success", lang), reply_markup=main_menu_kb(lang))
        elif status in ("waiting", "confirming", "sending"):
            await callback.answer(t("payment_pending", lang), show_alert=True)
        elif status == "expired":
            await answer_callback(callback, t("payment_expired", lang), reply_markup=subscription_kb(lang))
        else:
            await callback.answer(f"Status: {status}", show_alert=True)
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await callback.answer(t("error_generic", lang), show_alert=True)


@router.callback_query(F.data == "my_sub")
async def cb_my_subscription(callback: CallbackQuery, db_user: User, lang: str):
    """Show current subscription info."""
    text = t("my_subscription", lang,
             tier=db_user.tier.value.capitalize(),
             expires="∞" if db_user.tier == Tier.FREE else "N/A")
    await answer_callback(callback, text, reply_markup=subscription_kb(lang))
