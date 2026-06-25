"""
Alert engine — checks user alerts against real-time market data.
Supports 16 alert types with tier-based limits and per-user rate limiting.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, and_, func

from app.database import async_session
from app.models import UserAlert, AlertLog, User, AlertType, Tier


# ─── Tier limits ─────────────────────────────────────────
ALERT_LIMITS = {
    Tier.FREE: 1,
    Tier.PRO: 10,
    Tier.ELITE: 999,
}

# ─── Per-user rate limits (max notifications per hour) ───
RATE_LIMITS_PER_HOUR = {
    Tier.FREE: 3,
    Tier.PRO: 10,
    Tier.ELITE: 30,
}

# Global maximum per user per minute (burst protection)
MAX_PER_USER_PER_MINUTE = 2

# Alert types available per tier
ALERT_TYPES_BY_TIER = {
    Tier.FREE: {AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW},
    Tier.PRO: {
        AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW,
        AlertType.CHANGE_1H, AlertType.CHANGE_24H,
        AlertType.VOLUME_SPIKE, AlertType.RSI_OVERBOUGHT, AlertType.RSI_OVERSOLD,
        AlertType.MACD_CROSS, AlertType.BB_BREAKOUT,
        AlertType.NEW_ATH, AlertType.NEW_ATL,
        AlertType.CUSTOM_RANGE,
    },
    Tier.ELITE: set(AlertType),  # All types
}


class AlertEngine:
    """Checks all active user alerts against current market data."""

    def __init__(self):
        # Per-user notification timestamps for rate limiting
        self._user_notifications: dict[int, list[datetime]] = defaultdict(list)
        # Shared bot instance (lazy-initialized)
        self._bot = None

    def _check_user_rate_limit(self, user_id: int, tier: Tier) -> bool:
        """Return True if user can receive a notification, False if rate-limited."""
        now = datetime.now(timezone.utc)
        timestamps = self._user_notifications[user_id]

        # Clean up old entries (>1h)
        self._user_notifications[user_id] = [
            ts for ts in timestamps if now - ts < timedelta(hours=1)
        ]
        timestamps = self._user_notifications[user_id]

        # Check per-minute burst limit
        recent_minute = [ts for ts in timestamps if now - ts < timedelta(minutes=1)]
        if len(recent_minute) >= MAX_PER_USER_PER_MINUTE:
            return False

        # Check per-hour tier limit
        hourly_limit = RATE_LIMITS_PER_HOUR.get(tier, 3)
        if len(timestamps) >= hourly_limit:
            return False

        return True

    def _record_notification(self, user_id: int):
        """Record that a notification was sent to this user."""
        self._user_notifications[user_id].append(datetime.now(timezone.utc))

    async def check_all_alerts(self):
        """Main entry — fetch active alerts and check them."""
        async with async_session() as session:
            result = await session.execute(
                select(UserAlert).where(UserAlert.is_active == True)
            )
            alerts = result.scalars().all()

        if not alerts:
            return

        # Group by coin to minimize API calls
        by_coin: dict[str, list[UserAlert]] = {}
        for alert in alerts:
            by_coin.setdefault(alert.coin_symbol, []).append(alert)

        logger.debug(f"Checking {len(alerts)} alerts for {len(by_coin)} coins")

        from app.exchanges.manager import exchange_manager

        sem = asyncio.Semaphore(5)
        triggered = []

        async def _check_coin(coin: str, coin_alerts: list[UserAlert]):
            async with sem:
                try:
                    ticker = None
                    indicators = None

                    # Get price from best exchange
                    best = await exchange_manager.get_best_price(f"{coin}USDT")
                    if best.get("best_bid") is None:
                        return
                    price = (best["best_bid"] + best["best_ask"]) / 2

                    # Get ticker for volume/change data
                    for name in ("binance", "bybit", "okx"):
                        try:
                            ex = exchange_manager.get_exchange(name)
                            ticker = await ex.get_ticker(f"{coin}USDT")
                            break
                        except Exception:
                            continue

                    for alert in coin_alerts:
                        # Skip if in cooldown
                        if alert.last_triggered_at:
                            cooldown = timedelta(minutes=alert.cooldown_minutes)
                            if datetime.now(timezone.utc) - alert.last_triggered_at < cooldown:
                                continue

                        result = await self._check_single(alert, price, ticker, indicators)
                        if result:
                            # Confirmation: re-check price-based alerts after brief delay
                            needs_confirm = alert.alert_type in (
                                AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW,
                                AlertType.SUPPORT_HIT, AlertType.RESISTANCE_HIT,
                                AlertType.CUSTOM_RANGE,
                            )
                            if needs_confirm:
                                await asyncio.sleep(3)
                                best2 = await exchange_manager.get_best_price(f"{coin}USDT")
                                if best2.get("best_bid") is not None:
                                    price2 = (best2["best_bid"] + best2["best_ask"]) / 2
                                    result2 = await self._check_single(alert, price2, ticker, indicators)
                                    if not result2:
                                        logger.debug(f"Alert #{alert.id} not confirmed on re-check")
                                        continue
                                    result = result2  # Use updated price
                            triggered.append((alert, result))

                except Exception as e:
                    logger.debug(f"Alert check failed for {coin}: {e}")

        await asyncio.gather(*[_check_coin(c, a) for c, a in by_coin.items()])

        # Process triggered alerts with rate limiting
        if not triggered:
            return

        # Load user tiers for rate limiting
        user_ids = {a.user_id for a, _ in triggered}
        user_tiers: dict[int, Tier] = {}
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.id.in_(user_ids))
            )
            for user in result.scalars():
                user_tiers[user.id] = user.tier

        for alert, details in triggered:
            tier = user_tiers.get(alert.user_id, Tier.FREE)
            if not self._check_user_rate_limit(alert.user_id, tier):
                logger.debug(f"Rate limit hit for user {alert.user_id}, skipping alert #{alert.id}")
                continue
            await self._trigger_alert(alert, details)
            self._record_notification(alert.user_id)

    async def _check_single(
        self, alert: UserAlert, price: float, ticker, indicators
    ) -> dict | None:
        """Check a single alert. Returns trigger details or None."""
        params = alert.params or {}
        at = alert.alert_type

        if at == AlertType.PRICE_ABOVE:
            target = params.get("price", 0)
            if price >= target:
                return {"price": price, "target": target, "direction": "above"}

        elif at == AlertType.PRICE_BELOW:
            target = params.get("price", 0)
            if price <= target:
                return {"price": price, "target": target, "direction": "below"}

        elif at == AlertType.CHANGE_1H:
            threshold = params.get("percent", 5)
            if ticker and ticker.price_change_pct_24h is not None:
                # Approximate 1h change from recent candle data
                change_1h = await self._get_1h_change(alert.coin_symbol)
                if change_1h is not None and abs(change_1h) >= threshold:
                    return {"change": change_1h, "threshold": threshold}

        elif at == AlertType.CHANGE_24H:
            threshold = params.get("percent", 10)
            if ticker and abs(ticker.price_change_pct_24h) >= threshold:
                return {"change": ticker.price_change_pct_24h, "threshold": threshold}

        elif at == AlertType.VOLUME_SPIKE:
            multiplier = params.get("multiplier", 2.0)
            if ticker and ticker.volume_24h > 0:
                # Compare current volume against baseline using candle data
                baseline = await self._get_volume_baseline(alert.coin_symbol)
                if baseline and baseline > 0:
                    ratio = ticker.volume_24h / baseline
                    if ratio >= multiplier:
                        return {"volume": ticker.volume_24h, "baseline": baseline, "ratio": round(ratio, 2), "multiplier": multiplier}

        elif at == AlertType.RSI_OVERBOUGHT:
            threshold = params.get("level", 70)
            rsi = await self._get_rsi(alert.coin_symbol)
            if rsi is not None and rsi >= threshold:
                return {"rsi": rsi, "threshold": threshold}

        elif at == AlertType.RSI_OVERSOLD:
            threshold = params.get("level", 30)
            rsi = await self._get_rsi(alert.coin_symbol)
            if rsi is not None and rsi <= threshold:
                return {"rsi": rsi, "threshold": threshold}

        elif at == AlertType.BB_BREAKOUT:
            bb_data = await self._get_bb(alert.coin_symbol)
            if bb_data:
                if price > bb_data["upper"]:
                    return {"price": price, "bb_upper": bb_data["upper"], "direction": "above"}
                elif price < bb_data["lower"]:
                    return {"price": price, "bb_lower": bb_data["lower"], "direction": "below"}

        elif at == AlertType.CUSTOM_RANGE:
            low = params.get("low", 0)
            high = params.get("high", float("inf"))
            if price < low or price > high:
                return {"price": price, "low": low, "high": high}

        elif at == AlertType.MACD_CROSS:
            macd_data = await self._get_macd(alert.coin_symbol)
            if macd_data:
                direction = params.get("direction", "bullish")
                if direction == "bullish" and macd_data["cross"] == "bullish":
                    return {"macd": macd_data["histogram"], "cross": "bullish"}
                elif direction == "bearish" and macd_data["cross"] == "bearish":
                    return {"macd": macd_data["histogram"], "cross": "bearish"}
                elif direction == "any" and macd_data["cross"] in ("bullish", "bearish"):
                    return {"macd": macd_data["histogram"], "cross": macd_data["cross"]}

        elif at == AlertType.NEW_ATH:
            meta = await self._get_coin_meta(alert.coin_symbol)
            if meta and meta.get("ath") and price >= meta["ath"]:
                return {"price": price, "ath": meta["ath"]}

        elif at == AlertType.NEW_ATL:
            meta = await self._get_coin_meta(alert.coin_symbol)
            if meta and meta.get("atl") and price <= meta["atl"]:
                return {"price": price, "atl": meta["atl"]}

        elif at == AlertType.FUNDING_RATE:
            threshold = params.get("threshold", 0.1)
            rate = await self._get_funding_rate(alert.coin_symbol)
            if rate is not None and abs(rate) >= threshold:
                return {"rate": rate, "threshold": threshold}

        elif at == AlertType.SUPPORT_HIT:
            target = params.get("price", 0)
            tolerance = params.get("tolerance_pct", 0.5)
            if target > 0 and abs(price - target) / target * 100 <= tolerance:
                return {"price": price, "support": target}

        elif at == AlertType.RESISTANCE_HIT:
            target = params.get("price", 0)
            tolerance = params.get("tolerance_pct", 0.5)
            if target > 0 and abs(price - target) / target * 100 <= tolerance:
                return {"price": price, "resistance": target}

        return None

    async def _get_rsi(self, coin: str) -> float | None:
        """Compute RSI for a coin."""
        try:
            from app.exchanges.manager import exchange_manager
            from app.signals.analyzer import candles_to_df, compute_indicators

            for name in ("binance", "bybit", "okx"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    candles = await ex.get_candles(f"{coin}USDT", "1h", 20)
                    if len(candles) >= 14:
                        df = candles_to_df(candles)
                        ind = compute_indicators(df)
                        return ind.rsi_14
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_bb(self, coin: str) -> dict | None:
        """Get Bollinger Bands for a coin."""
        try:
            from app.exchanges.manager import exchange_manager
            from app.signals.analyzer import candles_to_df, compute_indicators

            for name in ("binance", "bybit", "okx"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    candles = await ex.get_candles(f"{coin}USDT", "1h", 25)
                    if len(candles) >= 20:
                        df = candles_to_df(candles)
                        ind = compute_indicators(df)
                        if ind.bb_upper and ind.bb_lower:
                            return {"upper": ind.bb_upper, "lower": ind.bb_lower}
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_funding_rate(self, coin: str) -> float | None:
        """Get current funding rate."""
        try:
            from app.exchanges.manager import exchange_manager
            for name in ("binance", "bybit"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    fr = await ex.get_funding_rate(f"{coin}USDT")
                    if fr:
                        return fr.rate
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_volume_baseline(self, coin: str) -> float | None:
        """Get average daily volume from recent candle history."""
        try:
            from app.exchanges.manager import exchange_manager
            for name in ("binance", "bybit", "okx"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    candles = await ex.get_candles(f"{coin}USDT", "1d", 7)
                    if len(candles) >= 3:
                        volumes = [c.volume for c in candles[:-1]]  # Exclude current day
                        return sum(volumes) / len(volumes) if volumes else None
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_macd(self, coin: str) -> dict | None:
        """Get MACD cross signal for a coin."""
        try:
            from app.exchanges.manager import exchange_manager
            from app.signals.analyzer import candles_to_df, compute_indicators

            for name in ("binance", "bybit", "okx"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    candles = await ex.get_candles(f"{coin}USDT", "1h", 30)
                    if len(candles) >= 26:
                        df = candles_to_df(candles)
                        ind = compute_indicators(df)
                        if ind.macd_histogram is not None:
                            # Detect cross by checking last 2 histograms
                            closes = df["close"].values
                            # Simple MACD cross detection
                            if len(df) >= 2:
                                macd_line = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
                                signal_line = macd_line.ewm(span=9).mean()
                                hist = macd_line - signal_line
                                if len(hist) >= 2:
                                    prev, curr = hist.iloc[-2], hist.iloc[-1]
                                    cross = None
                                    if prev <= 0 < curr:
                                        cross = "bullish"
                                    elif prev >= 0 > curr:
                                        cross = "bearish"
                                    if cross:
                                        return {"histogram": float(curr), "cross": cross}
                            return None
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_coin_meta(self, coin: str) -> dict | None:
        """Get coin metadata (ATH/ATL) from DB."""
        try:
            from app.models import CoinMeta
            async with async_session() as session:
                result = await session.execute(
                    select(CoinMeta).where(CoinMeta.symbol == f"{coin}USDT")
                )
                meta = result.scalar_one_or_none()
                if meta:
                    return {"ath": meta.ath, "atl": meta.atl}
        except Exception:
            pass
        return None

    async def _get_1h_change(self, coin: str) -> float | None:
        """Get actual 1h price change percentage from candle data."""
        try:
            from app.exchanges.manager import exchange_manager
            for name in ("binance", "bybit", "okx"):
                try:
                    ex = exchange_manager.get_exchange(name)
                    candles = await ex.get_candles(f"{coin}USDT", "1h", 2)
                    if len(candles) >= 2:
                        prev_close = candles[-2].close
                        curr_close = candles[-1].close
                        if prev_close > 0:
                            return (curr_close - prev_close) / prev_close * 100
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _trigger_alert(self, alert: UserAlert, details: dict):
        """Mark alert as triggered, log it, and send notification."""
        async with async_session() as session:
            # Reload from DB
            result = await session.execute(
                select(UserAlert).where(UserAlert.id == alert.id)
            )
            db_alert = result.scalar_one_or_none()
            if not db_alert:
                return

            db_alert.triggered_count += 1
            db_alert.last_triggered_at = datetime.now(timezone.utc)

            # One-shot alerts become inactive
            one_shot = {AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW,
                        AlertType.NEW_ATH, AlertType.NEW_ATL,
                        AlertType.SUPPORT_HIT, AlertType.RESISTANCE_HIT}
            if db_alert.alert_type in one_shot:
                db_alert.is_active = False
                db_alert.is_triggered = True

            log = AlertLog(
                alert_id=alert.id,
                user_id=alert.user_id,
                coin_symbol=alert.coin_symbol,
                alert_type=alert.alert_type,
                trigger_value=details.get("price") or details.get("rsi") or details.get("rate"),
                details=details,
            )
            session.add(log)
            await session.commit()

        # Send Telegram notification
        await self._notify_user(alert, details)

        logger.info(f"Alert #{alert.id} triggered: {alert.alert_type.value} for {alert.coin_symbol}")

    async def _get_bot(self):
        """Get or create a shared bot instance."""
        if self._bot is None:
            from app.config import settings
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            self._bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )
        return self._bot

    async def _notify_user(self, alert: UserAlert, details: dict):
        """Send trigger notification to the user's Telegram."""
        try:
            from app.localization.texts import t

            # Get user info
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == alert.user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return

            lang = user.language.value
            bot = await self._get_bot()
            text = self._format_alert_message(alert, details, lang)
            await bot.send_message(user.telegram_id, text)

        except Exception as e:
            logger.error(f"Failed to notify user for alert #{alert.id}: {e}")

    def _format_alert_message(self, alert: UserAlert, details: dict, lang: str) -> str:
        """Format alert trigger message."""
        from app.localization.texts import t

        coin = alert.coin_symbol
        at = alert.alert_type
        price = details.get("price", 0)

        header = t("alert.triggered_header", lang)
        type_name = t(f"alert.type_{at.value}", lang)

        if at in (AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW):
            target = details.get("target", 0)
            body = t("alert.price_hit_body", lang, coin=coin, price=f"${price:,.6g}", target=f"${target:,.6g}")
        elif at in (AlertType.CHANGE_1H, AlertType.CHANGE_24H):
            change = details.get("change", 0)
            body = t("alert.change_body", lang, coin=coin, change=f"{change:+.2f}%")
        elif at in (AlertType.RSI_OVERBOUGHT, AlertType.RSI_OVERSOLD):
            rsi = details.get("rsi", 0)
            body = t("alert.rsi_body", lang, coin=coin, rsi=f"{rsi:.1f}")
        elif at == AlertType.BB_BREAKOUT:
            direction = details.get("direction", "")
            body = t("alert.bb_body", lang, coin=coin, direction=direction, price=f"${price:,.6g}")
        elif at == AlertType.FUNDING_RATE:
            rate = details.get("rate", 0)
            body = t("alert.funding_body", lang, coin=coin, rate=f"{rate:.4f}%")
        elif at in (AlertType.SUPPORT_HIT, AlertType.RESISTANCE_HIT):
            level = details.get("support") or details.get("resistance", 0)
            body = t("alert.level_body", lang, coin=coin, price=f"${price:,.6g}", level=f"${level:,.6g}")
        elif at == AlertType.MACD_CROSS:
            cross = details.get("cross", "")
            body = t("alert.macd_body", lang, coin=coin, cross=cross)
        elif at == AlertType.NEW_ATH:
            ath = details.get("ath", 0)
            body = t("alert.ath_body", lang, coin=coin, price=f"${price:,.6g}", ath=f"${ath:,.6g}")
        elif at == AlertType.NEW_ATL:
            atl = details.get("atl", 0)
            body = t("alert.atl_body", lang, coin=coin, price=f"${price:,.6g}", atl=f"${atl:,.6g}")
        else:
            body = t("alert.generic_body", lang, coin=coin, price=f"${price:,.6g}")

        return f"{header}\n\n🏷 {type_name}\n{body}"


alert_engine = AlertEngine()
