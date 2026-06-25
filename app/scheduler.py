"""
Scheduler — APScheduler tasks for automated signal scanning, digests, subscription management.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger


scheduler = AsyncIOScheduler(timezone="UTC")


def setup_scheduler():
    """Register all scheduled jobs."""

    # ─── Signal scanning — every 5 minutes ──────
    scheduler.add_job(
        task_scan_signals,
        IntervalTrigger(minutes=5),
        id="scan_signals",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Track active signals — every 45 seconds ─
    scheduler.add_job(
        task_track_signals,
        IntervalTrigger(seconds=45),
        id="track_signals",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Fetch news — every 15 minutes ──────────
    scheduler.add_job(
        task_fetch_news,
        IntervalTrigger(minutes=15),
        id="fetch_news",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Daily digest — every day at 20:00 UTC ──
    scheduler.add_job(
        task_daily_digest,
        CronTrigger(hour=20, minute=0),
        id="daily_digest",
        replace_existing=True,
    )

    # ─── Weekly digest — Sunday 20:00 UTC ───────
    scheduler.add_job(
        task_weekly_digest,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_digest",
        replace_existing=True,
    )

    # ─── Subscription expiry check — every hour ─
    scheduler.add_job(
        task_check_subscriptions,
        IntervalTrigger(hours=1),
        id="check_subscriptions",
        replace_existing=True,
    )

    # ─── Market snapshots — every hour ──────────
    scheduler.add_job(
        task_market_snapshots,
        IntervalTrigger(hours=1),
        id="market_snapshots",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Self-learning correction — daily at 04:00 UTC ─
    scheduler.add_job(
        task_self_learning,
        CronTrigger(hour=4, minute=0),
        id="self_learning",
        replace_existing=True,
    )

    # ─── Check user alerts — every 45 seconds ───────
    scheduler.add_job(
        task_check_alerts,
        IntervalTrigger(seconds=45),
        id="check_alerts",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Collect candles (15m) — every 15 min ────────
    scheduler.add_job(
        task_collect_candles_15m,
        IntervalTrigger(minutes=15),
        id="collect_candles_15m",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Collect candles (1h) — every hour ───────────
    scheduler.add_job(
        task_collect_candles_1h,
        IntervalTrigger(hours=1),
        id="collect_candles_1h",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Collect candles (4h) — every 4 hours ───────
    scheduler.add_job(
        task_collect_candles_4h,
        IntervalTrigger(hours=4),
        id="collect_candles_4h",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Collect candles (1d) — daily at 00:30 UTC ──
    scheduler.add_job(
        task_collect_candles_1d,
        CronTrigger(hour=0, minute=30),
        id="collect_candles_1d",
        replace_existing=True,
    )

    # ─── Coin metadata refresh — daily at 03:00 UTC ─
    scheduler.add_job(
        task_refresh_coin_metadata,
        CronTrigger(hour=3, minute=0),
        id="refresh_coin_metadata",
        replace_existing=True,
    )

    # ─── Daily AI analysis — daily at 06:00 UTC ─────
    scheduler.add_job(
        task_daily_ai_analysis,
        CronTrigger(hour=6, minute=0),
        id="daily_ai_analysis",
        replace_existing=True,
    )

    # ─── Cleanup old candles — daily at 02:00 UTC ───
    scheduler.add_job(
        task_cleanup_old_data,
        CronTrigger(hour=2, minute=0),
        id="cleanup_old_data",
        replace_existing=True,
    )

    # ─── ML quality gate retrain — daily at 05:00 UTC ─
    scheduler.add_job(
        task_ml_retrain,
        CronTrigger(hour=5, minute=0),
        id="ml_retrain",
        replace_existing=True,
    )

    # ─── Wallet polling — every 60 seconds ──────────
    scheduler.add_job(
        task_poll_wallets,
        IntervalTrigger(seconds=60),
        id="poll_wallets",
        replace_existing=True,
        max_instances=1,
    )

    # ─── Wallet weekly digest — Sunday 19:00 UTC ────
    scheduler.add_job(
        task_wallet_weekly_digest,
        CronTrigger(day_of_week="sun", hour=19, minute=0),
        id="wallet_weekly_digest",
        replace_existing=True,
    )

    # ─── Wallet TX cleanup — daily at 02:30 UTC ─────
    scheduler.add_job(
        task_wallet_cleanup,
        CronTrigger(hour=2, minute=30),
        id="wallet_cleanup",
        replace_existing=True,
    )

    # ─── Missed signal reminders — every 4 hours ────
    scheduler.add_job(
        task_missed_signal_reminder,
        IntervalTrigger(hours=4),
        id="missed_signal_reminder",
        replace_existing=True,
        max_instances=1,
    )

    # ─── FREE channel delayed signals — every 2 hours ─
    scheduler.add_job(
        task_free_channel_delayed_signals,
        IntervalTrigger(hours=2),
        id="free_channel_delayed_signals",
        replace_existing=True,
        max_instances=1,
    )

    logger.info("Scheduler configured with all jobs")


# ─── Task Implementations ───────────────────────────────

async def task_scan_signals():
    """Scan for new trading signals."""
    try:
        from app.signals.engine import signal_engine
        from app.config import settings
        from app.redis_client import record_scan_heartbeat, increment_counter

        await record_scan_heartbeat()
        scan_num = await increment_counter("scans_today")
        logger.info(f"Starting signal scan #{scan_num}...")

        signals = await signal_engine.scan_all_pairs()

        await increment_counter("signals_today", 86400) if signals else None

        if signals:
            logger.info(f"Scan found {len(signals)} new signals")

            # Always push to WebSocket clients (even in DRY_RUN)
            try:
                from app.api.desktop import ws_manager
                for signal in signals:
                    await ws_manager.broadcast({
                        "type": "signal_new",
                        "signal": {
                            "id": signal.id,
                            "coin": signal.coin_symbol,
                            "direction": signal.direction.value,
                            "entry_price": signal.entry_price,
                            "tp1": signal.tp1,
                            "stop_loss": signal.stop_loss,
                            "confidence": signal.confidence_score,
                            "exchange": signal.exchange,
                            "timeframe": signal.timeframe,
                        },
                    })
            except Exception as e:
                logger.debug(f"WS broadcast failed: {e}")

            if settings.DRY_RUN:
                logger.info(f"DRY_RUN active — {len(signals)} signals saved but NOT broadcast")
            else:
                await _broadcast_new_signals(signals)
        else:
            logger.info("Scan complete: 0 signals generated")
    except Exception as e:
        logger.error(f"Signal scan task error: {e}", exc_info=True)


async def task_track_signals():
    """Track active signals for TP/SL hits."""
    try:
        from app.stats.tracker import signal_tracker
        await signal_tracker.check_all_active_signals()
    except Exception as e:
        logger.error(f"Signal tracking task error: {e}", exc_info=True)


async def task_fetch_news():
    """Fetch and parse crypto news from RSS feeds."""
    try:
        from app.data.news_parser import news_parser
        count = await news_parser.save_new_articles()
        if count > 0:
            logger.info(f"Fetched {count} new news articles")
    except Exception as e:
        logger.error(f"News fetch task error: {e}", exc_info=True)


async def task_daily_digest():
    """Generate and broadcast daily digest in both languages."""
    try:
        from app.config import settings
        from app.stats.reports import generate_daily_digest
        from app.images.digest import generate_digest_image

        digest = await generate_daily_digest()
        if digest.stats and digest.stats.total > 0:
            img_by_lang: dict[str, bytes] = {}
            for lang in ("uk", "en", "ru", "ar"):
                img_by_lang[lang] = await generate_digest_image(
                    period="daily",
                    date_range=digest.date_range,
                    total_signals=digest.stats.total,
                    win_rate=digest.stats.win_rate,
                    total_pnl=digest.stats.total_pnl,
                    tp1_rate=digest.stats.tp1_hit_rate,
                    tp2_rate=digest.stats.tp2_hit_rate,
                    tp3_rate=digest.stats.tp3_hit_rate,
                    top_signals=digest.top_signals,
                    lang=lang,
                )
            if settings.DRY_RUN:
                logger.info("DRY_RUN active — daily digest generated but NOT broadcast")
            else:
                await _broadcast_digest(img_by_lang, "daily")
    except Exception as e:
        logger.error(f"Daily digest task error: {e}", exc_info=True)


async def task_weekly_digest():
    """Generate and broadcast weekly digest in both languages."""
    try:
        from app.config import settings
        from app.stats.reports import generate_weekly_digest
        from app.images.digest import generate_digest_image

        digest = await generate_weekly_digest()
        if digest.stats and digest.stats.total > 0:
            img_by_lang: dict[str, bytes] = {}
            for lang in ("uk", "en", "ru", "ar"):
                img_by_lang[lang] = await generate_digest_image(
                    period="weekly",
                    date_range=digest.date_range,
                    total_signals=digest.stats.total,
                    win_rate=digest.stats.win_rate,
                    total_pnl=digest.stats.total_pnl,
                    tp1_rate=digest.stats.tp1_hit_rate,
                    tp2_rate=digest.stats.tp2_hit_rate,
                    tp3_rate=digest.stats.tp3_hit_rate,
                    top_signals=digest.top_signals,
                    lang=lang,
                )
            if settings.DRY_RUN:
                logger.info("DRY_RUN active — weekly digest generated but NOT broadcast")
            else:
                await _broadcast_digest(img_by_lang, "weekly")
    except Exception as e:
        logger.error(f"Weekly digest task error: {e}", exc_info=True)


async def task_check_subscriptions():
    """Check and expire overdue subscriptions."""
    try:
        from datetime import datetime, timezone
        from sqlalchemy import select, and_
        from app.database import async_session
        from app.models import Subscription, User, Tier

        async with async_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.expires_at <= datetime.now(timezone.utc),
                        Subscription.is_active == True,
                    )
                )
            )
            expired_subs = result.scalars().all()

            for sub in expired_subs:
                user_result = await session.execute(
                    select(User).where(User.id == sub.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user.tier = Tier.FREE
                    session.add(user)
                    logger.info(f"Subscription expired for user {user.telegram_id}")

                sub.is_active = False
                session.add(sub)

            await session.commit()
    except Exception as e:
        logger.error(f"Subscription check task error: {e}", exc_info=True)


async def task_self_learning():
    """Run self-learning correction cycle."""
    try:
        from app.ai.learning import self_learning
        await self_learning.apply_accumulated_corrections()
        logger.info("Self-learning correction cycle completed")
    except Exception as e:
        logger.error(f"Self-learning task error: {e}", exc_info=True)


async def task_check_alerts():
    """Check all active user alerts against market data."""
    try:
        from app.alerts.engine import alert_engine
        await alert_engine.check_all_alerts()
    except Exception as e:
        logger.error(f"Alert check task error: {e}", exc_info=True)


async def task_market_snapshots():
    """Save market state snapshots from all exchanges for learning & correlation.

    Improvements over old version:
    - Sorts by volume (not random API order)
    - Saves top 300 per exchange (up from 100)
    - Enriches with CoinGecko market_cap, 1h/7d price changes for top coins
    """
    try:
        from app.exchanges.manager import exchange_manager
        from app.database import async_session
        from app.models import MarketSnapshot
        from app.ai.vectorstore import store_market_context

        # Pre-fetch CoinGecko data for enrichment (market_cap, 1h, 7d changes)
        cg_data = {}
        try:
            from app.data.coingecko import coingecko
            market_list = await coingecko.get_market_data(
                per_page=250, page=1, sparkline=False,
                price_change_pct="1h,24h,7d",
            )
            for item in market_list:
                sym = item.get("symbol", "").upper() + "USDT"
                cg_data[sym] = {
                    "market_cap": item.get("market_cap"),
                    "change_1h": item.get("price_change_percentage_1h_in_currency"),
                    "change_7d": item.get("price_change_percentage_7d_in_currency"),
                }
        except Exception as e:
            logger.debug(f"CoinGecko enrichment fetch failed: {e}")

        snapshots_saved = 0
        for name, exchange in exchange_manager.exchanges.items():
            try:
                tickers = await exchange.get_all_tickers()
                # Sort by volume and take top 300
                tickers.sort(key=lambda t: t.volume_24h or 0, reverse=True)
                top_tickers = tickers[:300]

                async with async_session() as session:
                    for t in top_tickers:
                        cg = cg_data.get(t.symbol, {})
                        snap = MarketSnapshot(
                            coin_symbol=t.symbol,
                            exchange=name,
                            price=t.last_price,
                            volume_24h=t.volume_24h,
                            price_change_1h=cg.get("change_1h"),
                            price_change_24h=t.price_change_pct_24h,
                            price_change_7d=cg.get("change_7d"),
                            market_cap=cg.get("market_cap"),
                            extra_data={
                                "bid": t.bid,
                                "ask": t.ask,
                                "high": t.high_24h,
                                "low": t.low_24h,
                            },
                        )
                        session.add(snap)
                        snapshots_saved += 1
                    await session.commit()
            except Exception as e:
                logger.debug(f"Snapshot fetch from {name} failed: {e}")

        # Store aggregated market context as embedding for RAG
        if snapshots_saved > 0:
            try:
                btc_tickers = await exchange_manager.get_ticker_all_exchanges("BTCUSDT")
                eth_tickers = await exchange_manager.get_ticker_all_exchanges("ETHUSDT")

                btc_prices = [t.last_price for t in btc_tickers.values() if t]
                eth_prices = [t.last_price for t in eth_tickers.values() if t]
                btc_avg = sum(btc_prices) / len(btc_prices) if btc_prices else 0
                eth_avg = sum(eth_prices) / len(eth_prices) if eth_prices else 0

                summary = (
                    f"Market snapshot: BTC ${btc_avg:,.0f}, ETH ${eth_avg:,.0f}. "
                    f"Snapshots from {len(exchange_manager.exchanges)} exchanges, "
                    f"{snapshots_saved} data points saved."
                )
                await store_market_context(summary, {
                    "btc_price": btc_avg,
                    "eth_price": eth_avg,
                    "exchanges": list(exchange_manager.exchanges.keys()),
                    "snapshot_count": snapshots_saved,
                })
            except Exception as e:
                logger.debug(f"Market context embedding failed: {e}")

        logger.info(f"Market snapshots: {snapshots_saved} saved across {len(exchange_manager.exchanges)} exchanges")
    except Exception as e:
        logger.error(f"Market snapshot task error: {e}", exc_info=True)


# ─── Broadcasting Helpers ───────────────────────────────

async def _broadcast_new_signals(signals):
    """Send signal notifications to bot DM (personal messages) with inline buttons.

    NO channel posting — channels are used for digests/alpha feed only.
    Each user receives ONE signal notification matching their language + tier:
        - ELITE: full card + AI reasoning caption, with Details/Use buttons
        - PRO: full card with Details/Use buttons
        - FREE: free card with Subscribe CTA
    """
    from aiogram import Bot
    from aiogram.types import BufferedInputFile
    from sqlalchemy import select
    from app.config import settings
    from app.database import async_session
    from app.models import User, Signal as SignalModel, Tier
    from app.images.signal_card import generate_signal_card, generate_signal_card_free
    from app.localization.texts import t
    from app.bot.keyboards.inline import signal_notification_kb, signal_notification_free_kb

    bot = Bot(token=settings.BOT_TOKEN)

    try:
        for signal in signals:
            # ── Convert factors dict to list of readable strings ─
            raw_factors = signal.factors if isinstance(signal.factors, dict) else {}
            factors_list = []
            if raw_factors:
                pattern_data = raw_factors.get("patterns", {})
                for tf, patterns in pattern_data.items():
                    for p in patterns:
                        factors_list.append(f"{tf}: {p}")
                trend_data = raw_factors.get("trend", {})
                for tf, direction in trend_data.items():
                    factors_list.append(f"{tf} trend: {direction}")
                breakdown = raw_factors.get("score_breakdown", {})
                for component, val in breakdown.items():
                    if isinstance(val, (int, float)) and val > 0.5:
                        factors_list.append(f"{component}: {val:.0%}")

            # ── Pre-generate signal card images per language ─
            _card_args = dict(
                coin_symbol=signal.coin_symbol,
                direction=signal.direction.value,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                tp1=signal.tp1,
                tp2=signal.tp2,
                tp3=signal.tp3,
                confidence=signal.confidence_score,
                exchange=signal.exchange,
                leverage=signal.leverage_suggested,
                factors=factors_list,
            )
            img_full_by_lang: dict[str, bytes] = {}
            img_free_by_lang: dict[str, bytes] = {}
            for _lang in ("uk", "en", "ru", "ar"):
                img_full_by_lang[_lang] = await generate_signal_card(**_card_args, lang=_lang)

            # Serialize data for use outside ORM session scope
            sig_data = {
                "coin": signal.coin_symbol,
                "direction": signal.direction.value,
                "entry": signal.entry_price,
                "tp1": signal.tp1,
                "tp2": signal.tp2,
                "tp3": signal.tp3,
                "sl": signal.stop_loss,
                "confidence": signal.confidence_score,
                "leverage": signal.leverage_suggested,
                "min_tier": signal.min_tier,
                "factors": signal.factors if isinstance(signal.factors, dict) else {},
                "exchange": signal.exchange,
            }
            signal_id = signal.id

            # ── Compute approximate entry for FREE card ─────
            entry_approx = f"${signal.entry_price:,.4g}"
            potential_pct = abs(signal.tp1 - signal.entry_price) / signal.entry_price * 100 if signal.entry_price else 0

            # Pre-generate FREE cards per language
            for _lang in ("uk", "en", "ru", "ar"):
                img_free_by_lang[_lang] = await generate_signal_card_free(
                    coin_symbol=sig_data["coin"],
                    direction=sig_data["direction"],
                    entry_approx=entry_approx,
                    potential_pct=potential_pct,
                    confidence=sig_data["confidence"],
                    exchange=sig_data["exchange"],
                    lang=_lang,
                )

            direction_text = "🟢 LONG" if sig_data["direction"] == "LONG" else "🔴 SHORT"

            # ── DM each user (content matches their lang + tier) ─
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.is_active == True, User.is_banned == False)
                )
                users = result.scalars().all()

            tier_level = {Tier.FREE: 0, Tier.PRO: 1, Tier.ELITE: 2}
            signal_level = (
                tier_level.get(Tier(sig_data["min_tier"]), 0)
                if sig_data["min_tier"] else 0
            )

            for user in users:
                try:
                    lang = user.language.value
                    user_level = tier_level.get(user.tier, 0)

                    if user_level >= signal_level and user.tier != Tier.FREE:
                        # PRO/ELITE: full signal card + Details/Use buttons
                        caption = t(
                            "signal_dm_caption", lang,
                            coin=sig_data["coin"],
                            direction=direction_text,
                            exchange=sig_data["exchange"],
                            confidence=f"{sig_data['confidence']:.0f}",
                        )
                        img = img_full_by_lang.get(lang, img_full_by_lang["en"])
                        kb = signal_notification_kb(signal_id, lang)
                    else:
                        # FREE: teaser card + Subscribe CTA
                        caption = t(
                            "signal_dm_caption_free", lang,
                            coin=sig_data["coin"],
                            direction=direction_text,
                            potential=f"{potential_pct:.1f}",
                        )
                        img = img_free_by_lang.get(lang, img_free_by_lang["en"])
                        kb = signal_notification_free_kb(lang)

                    photo = BufferedInputFile(img, filename=f"signal_{sig_data['coin']}.png")
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=photo,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                except Exception:
                    pass  # User may have blocked the bot
    finally:
        await bot.session.close()


async def _broadcast_digest(img_bytes_by_lang: dict[str, bytes], period: str):
    """Send digest to 6 channels ONLY — channels are the content/digest hub.

    NO DMs — users get signals via bot DM, digests go to channels.

    Args:
        img_bytes_by_lang: {"uk": <png bytes>, "en": <png bytes>, "ru": <png bytes>}
        period: "daily" or "weekly"
    """
    from aiogram import Bot
    from aiogram.types import BufferedInputFile
    from app.config import settings
    from app.localization.texts import t

    bot = Bot(token=settings.BOT_TOKEN)

    try:
        for lang, img_bytes in img_bytes_by_lang.items():
            caption = t(f"digest_{period}_caption", lang)

            for tier in ("free", "pro"):
                cid = settings.get_channel_id(lang, tier)
                if not cid:
                    continue
                try:
                    photo = BufferedInputFile(img_bytes, filename=f"digest_{period}_{lang}.png")
                    await bot.send_photo(
                        chat_id=cid, photo=photo,
                        caption=caption, parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"Digest channel post {lang}_{tier} failed: {e}")
    finally:
        await bot.session.close()


# ─── Channel Content & Missed Signal Tasks ─────────────

async def task_missed_signal_reminder():
    """Push missed-signal reminders to users who haven't interacted with recent signals."""
    try:
        from datetime import datetime, timezone, timedelta
        from aiogram import Bot
        from sqlalchemy import select, func, and_
        from app.config import settings
        from app.database import async_session
        from app.models import User, Signal, SignalStatus, UserSignalAction, Tier
        from app.localization.texts import t
        from app.bot.keyboards.inline import missed_signals_kb

        if settings.DRY_RUN:
            return

        # Find signals created in the last 6 hours that are still active
        cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
        async with async_session() as session:
            result = await session.execute(
                select(func.count(Signal.id)).where(
                    Signal.created_at >= cutoff,
                    Signal.status.in_((
                        SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT,
                    )),
                )
            )
            recent_signal_count = result.scalar() or 0

            if recent_signal_count == 0:
                return

            # Get all recent signal IDs
            sig_result = await session.execute(
                select(Signal.id).where(
                    Signal.created_at >= cutoff,
                    Signal.status.in_((
                        SignalStatus.ACTIVE, SignalStatus.TP1_HIT, SignalStatus.TP2_HIT,
                    )),
                )
            )
            recent_signal_ids = [r[0] for r in sig_result.all()]

            # Get users (non-FREE) who haven't activated ANY recent signal
            all_users_result = await session.execute(
                select(User).where(
                    User.is_active == True,
                    User.is_banned == False,
                    User.tier != Tier.FREE,
                )
            )
            users = all_users_result.scalars().all()

        bot = Bot(token=settings.BOT_TOKEN)
        try:
            for user in users:
                # Check if user activated any recent signal
                async with async_session() as session:
                    activated = await session.execute(
                        select(func.count(UserSignalAction.id)).where(
                            UserSignalAction.user_id == user.id,
                            UserSignalAction.signal_id.in_(recent_signal_ids),
                        )
                    )
                    activated_count = activated.scalar() or 0

                missed = recent_signal_count - activated_count
                if missed <= 0:
                    continue

                try:
                    lang = user.language.value
                    text = t("missed_signals_reminder", lang, count=missed)
                    kb = missed_signals_kb(lang)
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                except Exception:
                    pass
        finally:
            await bot.session.close()

    except Exception as e:
        logger.error(f"Missed signal reminder error: {e}", exc_info=True)


async def task_free_channel_delayed_signals():
    """Post expired/closed signals to FREE channels as 'you missed this'.

    Signals closed in the last 2 hours get posted to FREE channels with result
    but without exact TP/SL levels — teaser to upgrade.
    """
    try:
        from datetime import datetime, timezone, timedelta
        from aiogram import Bot
        from aiogram.types import BufferedInputFile
        from sqlalchemy import select, and_
        from app.config import settings
        from app.database import async_session
        from app.models import Signal, SignalStatus
        from app.images.signal_card import generate_result_card
        from app.localization.texts import t

        if settings.DRY_RUN:
            return

        # Find signals that closed in the last 2 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        final_statuses = (
            SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
            SignalStatus.STOPPED, SignalStatus.CLOSED, SignalStatus.EXPIRED,
        )

        async with async_session() as session:
            result = await session.execute(
                select(Signal).where(
                    Signal.closed_at >= cutoff,
                    Signal.status.in_(final_statuses),
                    # Only post signals that haven't been posted to FREE channels yet
                    # Use message_ids JSON to track — if 'free_channel_posted' exists, skip
                )
            )
            signals = result.scalars().all()

        if not signals:
            return

        bot = Bot(token=settings.BOT_TOKEN)
        try:
            for signal in signals:
                # Skip if already posted to free channels
                msg_ids = signal.message_ids or {}
                if msg_ids.get("free_channel_posted"):
                    continue

                pnl = signal.pnl_percent or 0
                pnl_str = f"{pnl:+.2f}%"
                direction_text = "🟢 LONG" if signal.direction.value == "long" else "🔴 SHORT"

                for lang in ("uk", "en", "ru", "ar"):
                    free_cid = settings.get_channel_id(lang, "free")
                    if not free_cid:
                        continue

                    try:
                        caption = t(
                            "channel_missed_signal", lang,
                            coin=signal.coin_symbol,
                            direction=direction_text,
                            result=pnl_str,
                        )

                        # Generate result card for the channel post
                        entry = signal.entry_actual or signal.entry_price
                        exit_price = signal.exit_actual or signal.entry_price

                        result_type_map = {
                            SignalStatus.TP1_HIT: "tp1_hit",
                            SignalStatus.TP2_HIT: "tp2_hit",
                            SignalStatus.TP3_HIT: "tp3_hit",
                            SignalStatus.STOPPED: "sl_hit",
                        }
                        result_type = result_type_map.get(signal.status, "closed")

                        img = await generate_result_card(
                            coin_symbol=signal.coin_symbol,
                            direction=signal.direction.value,
                            result_type=result_type,
                            entry_price=entry,
                            exit_price=exit_price,
                            pnl_pct=pnl,
                            signal_id=signal.id,
                            lang=lang,
                        )
                        photo = BufferedInputFile(img, filename=f"result_{signal.coin_symbol}.png")
                        await bot.send_photo(
                            chat_id=free_cid, photo=photo,
                            caption=caption, parse_mode="HTML",
                        )
                    except Exception as e:
                        logger.warning(f"Free channel delayed post {lang} failed: {e}")

                # Mark as posted
                try:
                    async with async_session() as session:
                        sig_obj = await session.get(Signal, signal.id)
                        if sig_obj:
                            ids = sig_obj.message_ids or {}
                            ids["free_channel_posted"] = True
                            sig_obj.message_ids = ids
                            session.add(sig_obj)
                            await session.commit()
                except Exception:
                    pass
        finally:
            await bot.session.close()

    except Exception as e:
        logger.error(f"Free channel delayed signals error: {e}", exc_info=True)


# ─── Historical Data Collection Tasks ───────────────────

async def task_collect_candles_15m():
    """Collect 15-minute candles from all exchanges."""
    try:
        from app.data.collector import collect_candles
        from app.models import CandleTimeframe
        await collect_candles(CandleTimeframe.M15)
    except Exception as e:
        logger.error(f"Candle collector [15m] error: {e}", exc_info=True)


async def task_collect_candles_1h():
    """Collect 1-hour candles from all exchanges."""
    try:
        from app.data.collector import collect_candles
        from app.models import CandleTimeframe
        await collect_candles(CandleTimeframe.H1)
    except Exception as e:
        logger.error(f"Candle collector [1h] error: {e}", exc_info=True)


async def task_collect_candles_4h():
    """Collect 4-hour candles from all exchanges."""
    try:
        from app.data.collector import collect_candles
        from app.models import CandleTimeframe
        await collect_candles(CandleTimeframe.H4)
    except Exception as e:
        logger.error(f"Candle collector [4h] error: {e}", exc_info=True)


async def task_collect_candles_1d():
    """Collect daily candles from all exchanges."""
    try:
        from app.data.collector import collect_candles
        from app.models import CandleTimeframe
        await collect_candles(CandleTimeframe.D1)
    except Exception as e:
        logger.error(f"Candle collector [1d] error: {e}", exc_info=True)


async def task_refresh_coin_metadata():
    """Refresh coin metadata (logos, market cap, supply) from CoinGecko."""
    try:
        from app.data.collector import collect_coin_metadata
        await collect_coin_metadata()
    except Exception as e:
        logger.error(f"Coin metadata refresh error: {e}", exc_info=True)


async def task_daily_ai_analysis():
    """Run daily AI analysis for top coins and market overview."""
    try:
        from app.data.collector import run_daily_ai_analysis
        await run_daily_ai_analysis()
    except Exception as e:
        logger.error(f"Daily AI analysis error: {e}", exc_info=True)


async def task_cleanup_old_data():
    """Clean up old candles and AI analyses based on retention policy."""
    try:
        from app.data.collector import cleanup_old_candles
        await cleanup_old_candles()
    except Exception as e:
        logger.error(f"Data cleanup error: {e}", exc_info=True)


async def task_ml_retrain():
    """Retrain the LightGBM quality gate model from closed signal data."""
    try:
        from app.ml.quality_gate import quality_gate
        success = await quality_gate.retrain()
        if success:
            logger.info("ML quality gate retrained successfully")
        else:
            logger.debug("ML retrain skipped (not enough data or LightGBM unavailable)")
    except Exception as e:
        logger.error(f"ML retrain task error: {e}", exc_info=True)


async def task_poll_wallets():
    """Poll all tracked wallets for balance updates and new transactions."""
    try:
        from app.wallet.tracker import wallet_tracker
        await wallet_tracker.poll_all_wallets()
    except Exception as e:
        logger.error(f"Wallet poll task error: {e}", exc_info=True)


async def task_wallet_weekly_digest():
    """Send weekly wallet portfolio digests to users."""
    try:
        from app.wallet.analytics import send_weekly_digests
        await send_weekly_digests()
    except Exception as e:
        logger.error(f"Wallet weekly digest error: {e}", exc_info=True)


async def task_wallet_cleanup():
    """Clean up old wallet transactions (90 day retention)."""
    try:
        from app.wallet.tracker import wallet_tracker
        await wallet_tracker.cleanup_old_transactions(days=90)
    except Exception as e:
        logger.error(f"Wallet cleanup error: {e}", exc_info=True)
