"""
Auth middleware — registers users on first interaction, loads user data into handler context.
Uses Redis cache to avoid DB hit on every callback.
"""

import json
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from sqlalchemy import select
from loguru import logger

from app.database import async_session
from app.models import User, Language, Tier

_USER_CACHE_TTL = 300  # 5 minutes


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Extract user from event
        user_tg = None
        if isinstance(event, Message) and event.from_user:
            user_tg = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_tg = event.from_user

        if user_tg is None:
            return await handler(event, data)

        # Try Redis cache first
        user = await self._get_cached_user(user_tg.id)

        if user is None:
            # Cache miss — hit DB
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == user_tg.id)
                )
                user = result.scalar_one_or_none()

                if user is None:
                    # Register new user
                    user = User(
                        telegram_id=user_tg.id,
                        username=user_tg.username,
                        first_name=user_tg.first_name,
                        language=Language.UK,
                        tier=Tier.FREE,
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    logger.info(f"New user registered: {user_tg.id} (@{user_tg.username})")
                else:
                    # Update username/name if changed
                    changed = False
                    if user.username != user_tg.username:
                        user.username = user_tg.username
                        changed = True
                    if user.first_name != user_tg.first_name:
                        user.first_name = user_tg.first_name
                        changed = True
                    if changed:
                        session.add(user)
                        await session.commit()

            # Cache the user
            await self._cache_user(user)

        # Inject user into handler data
        data["db_user"] = user
        data["lang"] = user.language.value

        return await handler(event, data)

    @staticmethod
    async def _get_cached_user(telegram_id: int) -> User | None:
        """Try to load user from Redis cache."""
        try:
            from app.redis_client import redis_client
            if redis_client is None:
                return None
            raw = await redis_client.get(f"user:{telegram_id}")
            if raw is None:
                return None
            d = json.loads(raw)
            user = User(
                id=d["id"],
                telegram_id=d["telegram_id"],
                username=d.get("username"),
                first_name=d.get("first_name"),
                language=Language(d["language"]),
                tier=Tier(d["tier"]),
                is_active=d.get("is_active", True),
                is_banned=d.get("is_banned", False),
                referral_code=d.get("referral_code"),
            )
            return user
        except Exception:
            return None

    @staticmethod
    async def _cache_user(user: User) -> None:
        """Store user in Redis cache (5 min TTL)."""
        try:
            from app.redis_client import redis_client
            if redis_client is None:
                return
            d = {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "language": user.language.value,
                "tier": user.tier.value,
                "is_active": user.is_active,
                "is_banned": user.is_banned,
                "referral_code": user.referral_code,
            }
            await redis_client.setex(
                f"user:{user.telegram_id}",
                _USER_CACHE_TTL,
                json.dumps(d),
            )
        except Exception:
            pass

    @staticmethod
    async def invalidate_user_cache(telegram_id: int) -> None:
        """Call this when user data changes (tier upgrade, language change, etc.)."""
        try:
            from app.redis_client import redis_client
            if redis_client is None:
                return
            await redis_client.delete(f"user:{telegram_id}")
        except Exception:
            pass
