"""
Desktop API authentication — per-user API key validation.

Usage in endpoints:
    @router.get("/desktop/signals")
    async def get_signals(user: User = Depends(require_desktop_auth)):
        ...

    @router.get("/desktop/premium-feature")
    async def premium(user: User = Depends(require_tier(Tier.PRO))):
        ...
"""

import hashlib
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select

from app.database import async_session
from app.models import User, UserApiKey, Tier

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_desktop_auth(
    api_key: str | None = Security(_header),
) -> User:
    """Validate user API key and return the User object.

    Updates last_used_at on each successful call.
    """
    if not api_key:
        raise HTTPException(401, "Missing X-API-Key header")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    async with async_session() as session:
        result = await session.execute(
            select(UserApiKey)
            .where(UserApiKey.key_hash == key_hash, UserApiKey.is_active == True)
        )
        api_key_obj = result.scalar_one_or_none()

        if api_key_obj is None:
            raise HTTPException(401, "Invalid or revoked API key")

        # Touch last_used_at
        api_key_obj.last_used_at = datetime.now(timezone.utc)
        session.add(api_key_obj)
        await session.commit()

        user = api_key_obj.user
        if not user:
            raise HTTPException(401, "User not found for this key")
        if user.is_banned:
            raise HTTPException(403, "Account is banned")
        if not user.is_active:
            raise HTTPException(403, "Account is deactivated")

        return user


def require_tier(*allowed_tiers: Tier):
    """Dependency factory: require user to have one of the specified tiers.

    Usage:
        Depends(require_tier(Tier.PRO, Tier.ELITE))
    """
    _tier_level = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
    min_level = min(_tier_level.get(t, 0) for t in allowed_tiers)

    async def _check(user: User = Depends(require_desktop_auth)) -> User:
        user_level = _tier_level.get(user.tier, 0)
        if user_level < min_level:
            tier_names = "/".join(t.value.upper() for t in allowed_tiers)
            raise HTTPException(
                403,
                f"This feature requires {tier_names} tier. Current: {user.tier.value.upper()}",
            )
        return user

    return _check
