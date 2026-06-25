"""
Throttle middleware — prevents spam by limiting message frequency per user.
"""

import time
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self._user_timestamps: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None:
            now = time.monotonic()
            last = self._user_timestamps.get(user_id, 0)
            if now - last < self.rate_limit:
                # Throttled — silently ignore
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return
            self._user_timestamps[user_id] = now

            # Cleanup old entries periodically
            if len(self._user_timestamps) > 10000:
                cutoff = now - 60
                self._user_timestamps = {
                    uid: ts for uid, ts in self._user_timestamps.items() if ts > cutoff
                }

        return await handler(event, data)
