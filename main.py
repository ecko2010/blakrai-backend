"""
BLACK ROOM — main entry point.
Initializes DB, Redis, bot, scheduler, and FastAPI in one process.

IMPORTANT: Heavy imports (bot, handlers, DB) are deferred to lifespan()
so that uvicorn can bind the port and serve /health immediately.
"""

import os
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from loguru import logger
from fastapi import FastAPI, Request, Response

# Lightweight — no DB/Redis/Bot imports at module level
try:
    from app.config import settings
    from app.logging_config import setup_logging
    setup_logging(log_level=settings.LOG_LEVEL)
except Exception as e:
    # Even if config fails, let the process start so healthcheck works
    import sys
    print(f"WARNING: Config/logging init failed: {e}", file=sys.stderr)

    class _FallbackSettings:
        LOG_LEVEL = "INFO"
        TELEGRAM_BOT_TOKEN = ""
        BOT_TOKEN = ""
        DRY_RUN = False   # DO NOT default to True — it silently kills broadcasting
        ADMIN_API_KEY = ""
        ENVIRONMENT = "production"
        TELEGRAM_CHANNEL_UK_FREE = 0
        TELEGRAM_CHANNEL_UK_PRO = 0
        TELEGRAM_CHANNEL_EN_FREE = 0
        TELEGRAM_CHANNEL_EN_PRO = 0
        TELEGRAM_CHANNEL_RU_FREE = 0
        TELEGRAM_CHANNEL_RU_PRO = 0
        REDIS_URL = "redis://localhost:6379/0"
        def get_channel_id(self, lang, tier): return 0
        @property
        def all_channel_ids(self): return {}
    settings = _FallbackSettings()


# ─── Globals (populated in lifespan) ────────────────────
bot = None
dp = None
_polling_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown — all heavy init happens here, AFTER uvicorn binds."""
    global bot, dp, _polling_task

    logger.info("Starting BLACK ROOM...")

    # ── 0. Startup diagnostics ───────────────────────
    logger.info(f"  ENVIRONMENT   = {getattr(settings, 'ENVIRONMENT', '?')}")
    logger.info(f"  DRY_RUN       = {getattr(settings, 'DRY_RUN', '?')}")
    logger.info(f"  BOT_TOKEN     = {'SET' if getattr(settings, 'TELEGRAM_BOT_TOKEN', '') else 'MISSING'}")
    logger.info(f"  REDIS_URL     = {'SET' if getattr(settings, 'REDIS_URL', '') else 'MISSING'}")

    # Check channel configuration
    try:
        ch_map = settings.all_channel_ids
    except Exception:
        ch_map = {}
    if ch_map:
        logger.info(f"  Channels configured: {list(ch_map.keys())}")
    else:
        logger.warning("  ⚠ NO CHANNEL IDs configured! Signals will NOT be posted to channels.")
        logger.warning("  Set TELEGRAM_CHANNEL_UK_FREE, TELEGRAM_CHANNEL_UK_PRO, etc. in env vars.")

    if getattr(settings, 'DRY_RUN', False):
        logger.warning("  ⚠ DRY_RUN=True — signals will be saved to DB but NOT broadcast!")

    # ── 1. Database ──────────────────────────────────
    db_ok = False
    for attempt in range(1, 6):
        try:
            from app.database import init_db
            await init_db()
            logger.info("Database initialized")
            db_ok = True
            break
        except Exception as e:
            logger.warning(f"DB init attempt {attempt}/5 failed: {e}")
            if attempt < 5:
                await asyncio.sleep(3)
    if not db_ok:
        logger.error("Database init failed after 5 attempts")

    # ── 2. Redis ─────────────────────────────────────
    redis_ok = False
    for attempt in range(1, 4):
        try:
            from app.redis_client import init_redis
            await init_redis()
            logger.info("Redis connected")
            redis_ok = True
            break
        except Exception as e:
            logger.warning(f"Redis init attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                await asyncio.sleep(2)
    if not redis_ok:
        logger.error("Redis init failed after 3 attempts")

    # ── 3. Bot + Handlers ────────────────────────────
    try:
        from aiogram import Bot as AioBot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from app.bot.handlers import start, signals, stats, settings as settings_handler, payments, admin
        from app.bot.handlers import alerts as alerts_handler, watchlist as watchlist_handler
        from app.bot.handlers import wallet as wallet_handler
        from app.bot.handlers import signal_notifications as signal_notifications_handler
        from app.bot.middlewares.auth import AuthMiddleware
        from app.bot.middlewares.throttle import ThrottleMiddleware

        bot = AioBot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher()

        dp.message.middleware(ThrottleMiddleware(rate_limit=0.5))
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(ThrottleMiddleware(rate_limit=0.3))
        dp.callback_query.middleware(AuthMiddleware())

        dp.include_router(start.router)
        dp.include_router(signals.router)
        dp.include_router(stats.router)
        dp.include_router(settings_handler.router)
        dp.include_router(payments.router)
        dp.include_router(admin.router)
        dp.include_router(alerts_handler.router)
        dp.include_router(watchlist_handler.router)
        dp.include_router(wallet_handler.router)
        dp.include_router(signal_notifications_handler.router)

        logger.info("Bot configured")
    except Exception as e:
        logger.error(f"Bot setup failed: {e}")

    # ── 4. Scheduler ─────────────────────────────────
    scheduler = None
    if db_ok:
        try:
            from app.scheduler import scheduler, setup_scheduler
            setup_scheduler()
            scheduler.start()
            logger.info("Scheduler started (signal scan every 5 min, tracking every 45 sec)")
        except Exception as e:
            logger.error(f"Scheduler start failed: {e}")
    else:
        logger.error("Scheduler NOT started — database is unavailable, tasks would all fail")

    # ── 5. Admin API ─────────────────────────────────
    # (mounted at module level below, not here)

    # ── 5b. Public API ───────────────────────────────
    # (mounted at module level below, not here)

    # ── 5c. Desktop API ─────────────────────────────
    # (mounted at module level below, not here)

    # ── 6. Initial data collection (background) ─────
    if db_ok:
        async def _initial_data_collect():
            """Run initial backfill + metadata collection after 30s delay."""
            await asyncio.sleep(30)  # Let everything else start first
            try:
                from app.data.collector import collect_coin_metadata, backfill_candles
                logger.info("Starting initial coin metadata collection...")
                await collect_coin_metadata()
                logger.info("Starting initial candle backfill...")
                await backfill_candles()
            except Exception as e:
                logger.error(f"Initial data collection failed: {e}", exc_info=True)

        asyncio.create_task(_initial_data_collect())
        logger.info("Initial data collection scheduled (30s delay)")

    # ── 7. Bot polling ───────────────────────────────
    if bot and dp:
        _polling_task = asyncio.create_task(_start_bot_polling())
        logger.info("Bot polling started")

    logger.info("BLACK ROOM started successfully")
    yield

    # ── Shutdown ─────────────────────────────────────
    logger.info("Shutting down...")
    if scheduler:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
    if bot:
        await bot.session.close()
    try:
        from app.redis_client import close_redis
        await close_redis()
    except Exception:
        pass
    # Close exchange HTTP clients
    try:
        from app.exchanges.manager import exchange_manager
        await exchange_manager.close_all()
    except Exception:
        pass
    # Close OpenAI/DeepSeek HTTP clients to avoid AsyncHttpxClientWrapper errors
    try:
        from app.ai.deepseek import deepseek
        await deepseek._client.close()
    except Exception:
        pass
    try:
        from app.ai.vectorstore import _embedding_client
        if _embedding_client:
            await _embedding_client.close()
    except Exception:
        pass
    if _polling_task:
        _polling_task.cancel()
    logger.info("Shutdown complete")


app = FastAPI(title="BLACK ROOM API", lifespan=lifespan)

# CORS — allow admin panel, website, and desktop app
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://blackroom.app",
        "https://www.blackroom.app",
        "http://localhost:3000",
        "http://localhost:5173",   # Desktop app dev (Vite)
        "http://localhost:8080",   # Desktop app dev alt
        "http://localhost:1420",   # Tauri dev server
        "tauri://localhost",       # Tauri desktop app
        "https://tauri.localhost", # Tauri desktop app (alt)
        "http://tauri.localhost",  # Tauri prod
        "app://blackroom",         # Electron custom scheme
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount docs page at / (lightweight, no DB needed)
from app.api.docs_page import router as docs_router
app.include_router(docs_router)

# ─── Mount API routers at module level (before middleware stack finalises) ───

try:
    from app.api.public import router as public_api_router
    app.include_router(public_api_router)
    logger.info("Public API mounted at /public")
except Exception as e:
    logger.error(f"Public API mount failed: {e}")

try:
    from app.api.desktop import router as desktop_api_router
    app.include_router(desktop_api_router)
    logger.info("Desktop API mounted at /desktop")
except Exception as e:
    logger.error(f"Desktop API mount failed: {e}")

try:
    from app.admin.router import router as admin_panel_router
    app.include_router(admin_panel_router)
    logger.info("Admin panel mounted at /admin")
except Exception as e:
    logger.error(f"Admin panel mount failed: {e}")


async def _start_bot_polling():
    """Start bot long polling in background."""
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Bot polling error: {e}")


# ─── API Routes (always available) ─────────────────────

@app.get("/health")
async def health():
    from app.redis_client import get_scan_heartbeat, redis_client as _rc

    last_scan = await get_scan_heartbeat()

    # DB check
    db_ok = False
    signals_count = 0
    active_signals = 0
    try:
        from app.database import async_session
        from sqlalchemy import select, func, text
        from app.models import Signal, SignalStatus
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
            signals_count = await session.scalar(select(func.count(Signal.id))) or 0
            active_signals = await session.scalar(
                select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
            ) or 0
    except Exception:
        pass

    # Scheduler check
    scheduler_running = False
    scheduler_jobs = 0
    try:
        from app.scheduler import scheduler as _sched
        scheduler_running = _sched.running
        scheduler_jobs = len(_sched.get_jobs())
    except Exception:
        pass

    # Channel config
    try:
        ch_map = settings.all_channel_ids
    except Exception:
        ch_map = {}

    return {
        "status": "ok",
        "service": "blackroom",
        "bot_active": bot is not None,
        "dry_run": getattr(settings, "DRY_RUN", None),
        "db_ok": db_ok,
        "redis_ok": _rc is not None,
        "scheduler_running": scheduler_running,
        "scheduler_jobs": scheduler_jobs,
        "last_scan": last_scan,
        "total_signals": signals_count,
        "active_signals": active_signals,
        "channels_configured": len(ch_map),
    }


@app.post("/webhooks/nowpayments")
async def nowpayments_webhook(request: Request):
    """Process NOWPayments IPN callbacks."""
    from app.payments.nowpayments import nowpayments_client

    body = await request.body()
    signature = request.headers.get("x-nowpayments-sig", "")

    if not await nowpayments_client.verify_ipn(body, signature):
        return Response(status_code=403, content="Invalid signature")

    import json
    data = json.loads(body)
    await nowpayments_client.process_ipn(data)

    return {"status": "ok"}


# ─── Entry Point ────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    log_level = getattr(settings, "LOG_LEVEL", "INFO").lower()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
    )
