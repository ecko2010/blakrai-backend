"""
Bot UX utilities — safe message editing/deletion for clean menu transitions.
"""

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
from loguru import logger


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message | None:
    """Edit message text safely, handling MessageNotModified and other errors."""
    try:
        return await message.edit_text(
            text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except TelegramBadRequest as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return None  # Content identical — ignore
        if "message can't be edited" in err or "message to edit not found" in err:
            # Message too old or deleted — send a new one
            return await message.answer(
                text, reply_markup=reply_markup, parse_mode=parse_mode
            )
        logger.debug(f"safe_edit_text error: {e}")
        return None


async def safe_delete(message: Message) -> bool:
    """Delete a message safely, suppressing 'can't be deleted' errors."""
    try:
        await message.delete()
        return True
    except TelegramBadRequest:
        return False


async def answer_callback(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message | None:
    """Standard callback response: ack FIRST (removes spinner), then edit message."""
    await callback.answer()
    result = await safe_edit_text(
        callback.message, text, reply_markup=reply_markup, parse_mode=parse_mode
    )
    return result


async def send_and_cleanup(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> Message | None:
    """Delete the old message and send a brand new one (useful when switching
    from text to photo or vice versa)."""
    await callback.answer()
    await safe_delete(callback.message)
    msg = await callback.message.answer(
        text, reply_markup=reply_markup, parse_mode=parse_mode
    )
    return msg
