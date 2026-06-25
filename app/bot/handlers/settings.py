"""
Settings handler — language, notifications, API keys for desktop app.
"""

import secrets
import hashlib
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.models import User, UserApiKey
from app.database import async_session
from app.localization.texts import t
from app.bot.keyboards.inline import settings_kb, language_kb, main_menu_kb
from app.bot.keyboards.reply import settings_reply_kb
from app.bot.utils import answer_callback, safe_delete

router = Router()


@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery, db_user: User, lang: str):
    """Show settings menu + swap reply keyboard."""
    await callback.answer()
    from app.bot.handlers.start import _last_bot_msg, _send_or_edit
    chat_id = callback.message.chat.id
    _last_bot_msg[chat_id] = callback.message.message_id
    tier_name = db_user.tier.value.capitalize()
    await _send_or_edit(
        chat_id, callback.bot,
        text=t("settings", lang, tier=tier_name),
        reply_markup=settings_kb(lang),
        reply_kb=settings_reply_kb(lang),
    )


@router.callback_query(F.data == "notifications_settings")
async def cb_notifications(callback: CallbackQuery, db_user: User, lang: str):
    """Toggle notification preferences. Placeholder for now."""
    await callback.answer(t("coming_soon", lang), show_alert=True)


# ─── API Key Management ────────────────────────────────

@router.callback_query(F.data == "api_key_menu")
async def cb_api_key_menu(callback: CallbackQuery, db_user: User, lang: str):
    """Show API key management menu."""
    from app.bot.keyboards.inline import api_key_menu_kb

    # Check existing keys
    async with async_session() as session:
        result = await session.execute(
            select(UserApiKey).where(
                UserApiKey.user_id == db_user.id,
                UserApiKey.is_active == True,
            )
        )
        active_keys = result.scalars().all()

    if active_keys:
        key = active_keys[0]
        last_used = key.last_used_at.strftime("%d.%m.%Y %H:%M") if key.last_used_at else "—"
        text = t("api_key_info", lang,
                 prefix=key.key_prefix,
                 created=key.created_at.strftime("%d.%m.%Y"),
                 last_used=last_used)
    else:
        text = t("api_key_none", lang)

    await answer_callback(callback, text, reply_markup=api_key_menu_kb(lang, has_key=bool(active_keys)))


@router.callback_query(F.data == "api_key_generate")
async def cb_api_key_generate(callback: CallbackQuery, db_user: User, lang: str):
    """Generate a new API key for desktop app."""
    from app.bot.keyboards.inline import api_key_menu_kb

    # Revoke all existing keys
    async with async_session() as session:
        result = await session.execute(
            select(UserApiKey).where(
                UserApiKey.user_id == db_user.id,
                UserApiKey.is_active == True,
            )
        )
        for old_key in result.scalars().all():
            old_key.is_active = False
            from datetime import datetime, timezone
            old_key.revoked_at = datetime.now(timezone.utc)
            session.add(old_key)

        # Generate new key: brk_<40 hex chars>
        raw_key = "brk_" + secrets.token_hex(20)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        new_key = UserApiKey(
            user_id=db_user.id,
            key_hash=key_hash,
            key_prefix=raw_key[:12],
            name="Desktop App",
        )
        session.add(new_key)
        await session.commit()

    text = t("api_key_created", lang, api_key=raw_key)
    await answer_callback(callback, text, reply_markup=api_key_menu_kb(lang, has_key=True))


@router.callback_query(F.data == "api_key_revoke")
async def cb_api_key_revoke(callback: CallbackQuery, db_user: User, lang: str):
    """Revoke all API keys."""
    from app.bot.keyboards.inline import api_key_menu_kb
    from datetime import datetime, timezone

    async with async_session() as session:
        result = await session.execute(
            select(UserApiKey).where(
                UserApiKey.user_id == db_user.id,
                UserApiKey.is_active == True,
            )
        )
        count = 0
        for key in result.scalars().all():
            key.is_active = False
            key.revoked_at = datetime.now(timezone.utc)
            session.add(key)
            count += 1
        await session.commit()

    text = t("api_key_revoked", lang)
    await answer_callback(callback, text, reply_markup=api_key_menu_kb(lang, has_key=False))
