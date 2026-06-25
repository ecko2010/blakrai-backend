import redis.asyncio as redis
from app.config import settings
from loguru import logger


redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global redis_client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    await redis_client.ping()
    logger.info("Redis connected")
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis closed")


def get_redis() -> redis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


# ─── Helpers used by other modules ──────────────────────

async def set_signal_cooldown(coin: str, ttl_seconds: int = 14400) -> None:
    """Mark coin as on cooldown (default 4h). Used by signal engine."""
    if redis_client is None:
        return
    try:
        await redis_client.setex(f"cooldown:{coin}", ttl_seconds, "1")
    except Exception as e:
        logger.debug(f"Redis cooldown set failed: {e}")


async def is_on_cooldown(coin: str) -> bool:
    """Check if coin is still on cooldown."""
    if redis_client is None:
        return False  # Fall back to DB check if Redis unavailable
    try:
        return bool(await redis_client.exists(f"cooldown:{coin}"))
    except Exception:
        return False


async def record_scan_heartbeat() -> None:
    """Store last scan timestamp so we can monitor liveness."""
    if redis_client is None:
        return
    try:
        from datetime import datetime, timezone
        await redis_client.set("last_scan_ts", datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


async def get_scan_heartbeat() -> str | None:
    """Get last scan timestamp."""
    if redis_client is None:
        return None
    try:
        return await redis_client.get("last_scan_ts")
    except Exception:
        return None


async def increment_counter(key: str, ttl_seconds: int = 86400) -> int:
    """Increment a daily counter (e.g. signals_today, scans_today). Resets via TTL."""
    if redis_client is None:
        return 0
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        results = await pipe.execute()
        return results[0]
    except Exception:
        return 0
