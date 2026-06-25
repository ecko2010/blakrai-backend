"""
Signal tracker — monitors active signals, detects TP/SL hits, updates status.
CORRECT handling of partial TP hits (TP1 hit but later SL hit is NOT a full loss).
"""

import asyncio
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Signal, SignalUpdate, SignalStatus, SignalDirection, UpdateType
from app.exchanges.manager import exchange_manager


class SignalTracker:
    """Tracks active signals in real-time, updates statuses on TP/SL hits."""

    async def check_all_active_signals(self):
        """Check all active/in-progress signals against current prices."""
        # Track ALL non-final signals: ACTIVE, TP1_HIT, TP2_HIT
        trackable = (
            SignalStatus.ACTIVE,
            SignalStatus.TP1_HIT,
            SignalStatus.TP2_HIT,
        )
        async with async_session() as session:
            result = await session.execute(
                select(Signal).where(Signal.status.in_(trackable))
            )
            active_signals = result.scalars().all()

        if not active_signals:
            return

        logger.debug(f"Tracking {len(active_signals)} active signals")

        # Process signals in parallel (max 5 concurrent to avoid rate limits)
        sem = asyncio.Semaphore(5)

        async def _safe_check(sig):
            async with sem:
                try:
                    await self._check_signal(sig)
                except Exception as e:
                    logger.error(f"Error tracking signal #{sig.id}: {e}")

        await asyncio.gather(*[_safe_check(s) for s in active_signals])

    async def _check_signal(self, signal: Signal):
        """Check a single signal against current market price."""
        # Get current price from the signal's exchange
        try:
            exchange = exchange_manager.get_exchange(signal.exchange.lower())
            ticker = await exchange.get_ticker(signal.pair)
            current_price = ticker.last_price
        except Exception:
            # Fallback: try ALL exchanges, ordered by scoring
            from app.exchanges.scoring import exchange_scorer
            all_exchanges = list(exchange_manager.exchanges.keys())
            ordered = exchange_scorer.get_ordered_list(all_exchanges)
            current_price = None
            for fb_name in ordered:
                if fb_name == signal.exchange.lower():
                    continue
                try:
                    fb_exchange = exchange_manager.get_exchange(fb_name)
                    fb_ticker = await fb_exchange.get_ticker(signal.pair)
                    current_price = fb_ticker.last_price
                    break
                except Exception:
                    continue
            if current_price is None:
                logger.debug(f"No price available for {signal.pair}")
                return

        is_long = signal.direction == SignalDirection.LONG

        # Track peak profit and max drawdown for statistics
        entry = signal.entry_actual or signal.entry_price
        if is_long:
            current_pnl = (current_price - entry) / entry * 100
        else:
            current_pnl = (entry - current_price) / entry * 100

        peak_profit = signal.peak_profit_percent or 0
        max_dd = signal.max_drawdown_percent or 0

        if current_pnl > peak_profit:
            peak_profit = current_pnl
        if current_pnl < max_dd:
            max_dd = current_pnl

        # Check entry hit (if we're tracking entry zone)
        entry_just_hit = False
        if signal.entry_actual is None:
            if is_long and current_price <= signal.entry_price:
                entry_just_hit = True
                signal.entry_actual = current_price
            elif not is_long and current_price >= signal.entry_price:
                entry_just_hit = True
                signal.entry_actual = current_price

        # ─── TRAILING STOP ────────────────────────────────
        # 1. Dynamic trailing: if unrealized profit > 3%, trail SL to lock 50% of gains
        # 2. After TP1 hit: SL → breakeven.  After TP2 hit: SL → TP1.
        trailing_sl_updated = False

        # Dynamic profit trailing (applies even before TP1 hit)
        if current_pnl > 3.0:
            # Lock 50% of unrealized profit via trailing SL
            lock_pct = current_pnl * 0.5
            if is_long:
                dynamic_sl = entry * (1 + lock_pct / 100)
                if dynamic_sl > signal.stop_loss:
                    signal.stop_loss = round(dynamic_sl, 6)
                    trailing_sl_updated = True
                    logger.debug(f"Signal #{signal.id}: dynamic trail SL → {signal.stop_loss} (lock {lock_pct:.1f}%)")
            else:
                dynamic_sl = entry * (1 - lock_pct / 100)
                if dynamic_sl < signal.stop_loss:
                    signal.stop_loss = round(dynamic_sl, 6)
                    trailing_sl_updated = True
                    logger.debug(f"Signal #{signal.id}: dynamic trail SL → {signal.stop_loss} (lock {lock_pct:.1f}%)")

        # TP-level trailing (overrides dynamic trail if more aggressive)
        if signal.status == SignalStatus.TP1_HIT:
            # Trail SL to breakeven
            if is_long and signal.stop_loss < entry:
                signal.stop_loss = entry
                trailing_sl_updated = True
                logger.debug(f"Signal #{signal.id}: trailing SL → breakeven {entry}")
            elif not is_long and signal.stop_loss > entry:
                signal.stop_loss = entry
                trailing_sl_updated = True
                logger.debug(f"Signal #{signal.id}: trailing SL → breakeven {entry}")
        elif signal.status == SignalStatus.TP2_HIT:
            # Trail SL to TP1 level
            if is_long and signal.stop_loss < signal.tp1:
                signal.stop_loss = signal.tp1
                trailing_sl_updated = True
                logger.debug(f"Signal #{signal.id}: trailing SL → TP1 {signal.tp1}")
            elif not is_long and signal.stop_loss > signal.tp1:
                signal.stop_loss = signal.tp1
                trailing_sl_updated = True
                logger.debug(f"Signal #{signal.id}: trailing SL → TP1 {signal.tp1}")

        # ─── TP/SL CHECK ─────────────────────────────────
        # IMPORTANT LOGIC: If TP1 was already hit, the REMAINING position might hit SL,
        # but the overall trade is NOT a full loss. We track this correctly.

        already_hit_tp1 = signal.status in (SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT)
        already_hit_tp2 = signal.status in (SignalStatus.TP2_HIT, SignalStatus.TP3_HIT)
        already_hit_tp3 = signal.status == SignalStatus.TP3_HIT

        new_status = None
        pnl = None

        if is_long:
            # Check TPs (highest first)
            if signal.tp3 and current_price >= signal.tp3 and not already_hit_tp3:
                new_status = SignalStatus.TP3_HIT
                pnl = (signal.tp3 - entry) / entry * 100
            elif signal.tp2 and current_price >= signal.tp2 and not already_hit_tp2:
                new_status = SignalStatus.TP2_HIT
                pnl = (signal.tp2 - entry) / entry * 100
            elif current_price >= signal.tp1 and not already_hit_tp1:
                new_status = SignalStatus.TP1_HIT
                pnl = (signal.tp1 - entry) / entry * 100
            elif current_price <= signal.stop_loss:
                if already_hit_tp1:
                    new_status = SignalStatus.CLOSED
                    tp1_pnl = (signal.tp1 - entry) / entry * 100
                    sl_pnl = (signal.stop_loss - entry) / entry * 100
                    if already_hit_tp2:
                        # 33% closed at TP1 + 33% closed at TP2 + 34% at trailing SL (=TP1)
                        tp2_pnl = (signal.tp2 - entry) / entry * 100
                        pnl = tp1_pnl * 0.33 + tp2_pnl * 0.33 + sl_pnl * 0.34
                    else:
                        # 33% closed at TP1, 67% at SL
                        pnl = tp1_pnl * 0.33 + sl_pnl * 0.67
                else:
                    new_status = SignalStatus.STOPPED
                    pnl = (signal.stop_loss - entry) / entry * 100
        else:
            # Short positions
            if signal.tp3 and current_price <= signal.tp3 and not already_hit_tp3:
                new_status = SignalStatus.TP3_HIT
                pnl = (entry - signal.tp3) / entry * 100
            elif signal.tp2 and current_price <= signal.tp2 and not already_hit_tp2:
                new_status = SignalStatus.TP2_HIT
                pnl = (entry - signal.tp2) / entry * 100
            elif current_price <= signal.tp1 and not already_hit_tp1:
                new_status = SignalStatus.TP1_HIT
                pnl = (entry - signal.tp1) / entry * 100
            elif current_price >= signal.stop_loss:
                if already_hit_tp1:
                    new_status = SignalStatus.CLOSED
                    tp1_pnl = (entry - signal.tp1) / entry * 100
                    sl_pnl = (entry - signal.stop_loss) / entry * 100
                    if already_hit_tp2:
                        tp2_pnl = (entry - signal.tp2) / entry * 100
                        pnl = tp1_pnl * 0.33 + tp2_pnl * 0.33 + sl_pnl * 0.34
                    else:
                        pnl = tp1_pnl * 0.33 + sl_pnl * 0.67
                else:
                    new_status = SignalStatus.STOPPED
                    pnl = (entry - signal.stop_loss) / entry * 100

        # Check expiration
        if new_status is None and signal.expires_at and datetime.now(timezone.utc) > signal.expires_at:
            if already_hit_tp1:
                new_status = SignalStatus.CLOSED
                if is_long:
                    tp1_pnl = (signal.tp1 - entry) / entry * 100
                    tp2_pnl = (signal.tp2 - entry) / entry * 100 if signal.tp2 else tp1_pnl
                else:
                    tp1_pnl = (entry - signal.tp1) / entry * 100
                    tp2_pnl = (entry - signal.tp2) / entry * 100 if signal.tp2 else tp1_pnl
                remainder_pnl = current_pnl
                if already_hit_tp2:
                    # 33% at TP1 + 33% at TP2 + 34% at current price
                    pnl = tp1_pnl * 0.33 + tp2_pnl * 0.33 + remainder_pnl * 0.34
                else:
                    # 33% at TP1 + 67% at current price
                    pnl = tp1_pnl * 0.33 + remainder_pnl * 0.67
            else:
                new_status = SignalStatus.EXPIRED
                pnl = current_pnl

        # Update signal if status changed
        if new_status and new_status != signal.status:
            update_type = self._status_to_update_type(new_status)
            await self._update_signal_status(
                signal, new_status, current_price, pnl, peak_profit, max_dd, update_type,
                entry_just_hit=entry_just_hit,
            )
        else:
            # Persist tracking fields (entry_actual, peak, drawdown, trailing SL) EVERY cycle
            async with async_session() as session:
                stmt = (
                    select(Signal).where(Signal.id == signal.id)
                )
                result = await session.execute(stmt)
                db_signal = result.scalar_one()
                db_signal.peak_profit_percent = peak_profit
                db_signal.max_drawdown_percent = max_dd
                if entry_just_hit:
                    db_signal.entry_actual = signal.entry_actual
                if trailing_sl_updated:
                    db_signal.stop_loss = signal.stop_loss
                await session.commit()

    async def _update_signal_status(
        self,
        signal: Signal,
        new_status: SignalStatus,
        price: float,
        pnl: float | None,
        peak_profit: float,
        max_dd: float,
        update_type: UpdateType,
        entry_just_hit: bool = False,
    ):
        """Update signal status and create update record."""
        is_final = new_status in (SignalStatus.STOPPED, SignalStatus.TP3_HIT, SignalStatus.CLOSED, SignalStatus.EXPIRED)

        async with async_session() as session:
            # Reload fresh from DB to avoid detached object issues
            result = await session.execute(
                select(Signal).where(Signal.id == signal.id)
            )
            db_signal = result.scalar_one()

            db_signal.status = new_status
            db_signal.pnl_percent = round(pnl, 4) if pnl is not None else None
            db_signal.peak_profit_percent = peak_profit
            db_signal.max_drawdown_percent = max_dd
            if entry_just_hit and signal.entry_actual:
                db_signal.entry_actual = signal.entry_actual
            if is_final:
                db_signal.closed_at = datetime.now(timezone.utc)
                db_signal.exit_actual = price

            update = SignalUpdate(
                signal_id=signal.id,
                update_type=update_type,
                price_at_update=price,
                details={
                    "pnl": round(pnl, 4) if pnl else None,
                    "peak_profit": round(peak_profit, 4),
                    "max_drawdown": round(max_dd, 4),
                },
            )
            session.add(update)
            await session.commit()

        logger.info(
            f"Signal #{signal.id} {signal.coin_symbol}: "
            f"{signal.status.value} @ {price} (PnL: {pnl:.2f}%)"
            if pnl else f"Signal #{signal.id}: {signal.status.value}"
        )

        # Push update to WebSocket clients
        try:
            from app.api.desktop import ws_manager
            await ws_manager.broadcast({
                "type": "signal_update",
                "signal": {
                    "id": signal.id,
                    "coin": signal.coin_symbol,
                    "status": new_status.value,
                    "price": price,
                    "pnl": round(pnl, 4) if pnl else None,
                    "peak_profit": round(peak_profit, 4),
                    "is_final": is_final,
                },
            })
        except Exception:
            pass

        # ── Notify users who activated this signal via Telegram ──
        try:
            await self._notify_signal_subscribers(
                signal, new_status, price, pnl, is_final, update_type,
            )
        except Exception as e:
            logger.error(f"Telegram notification for signal #{signal.id} failed: {e}")

        # Trigger learning for final statuses
        if is_final:
            signal_id = signal.id
            async def _safe_learn(sid: int):
                try:
                    from app.ai.learning import self_learning
                    await self_learning.process_signal_outcome(sid)
                except Exception as e:
                    logger.error(f"Learning task failed for signal #{sid}: {e}")
            asyncio.create_task(_safe_learn(signal_id))

    async def _notify_signal_subscribers(
        self,
        signal: Signal,
        new_status: SignalStatus,
        price: float,
        pnl: float | None,
        is_final: bool,
        update_type: UpdateType,
    ):
        """Send Telegram notification + result card to users who activated this signal."""
        from aiogram import Bot
        from aiogram.types import BufferedInputFile
        from sqlalchemy import select
        from app.config import settings
        from app.database import async_session as get_session
        from app.models import User, UserSignalAction
        from app.images.signal_card import generate_result_card
        from app.localization.texts import t
        from app.bot.keyboards.inline import signal_update_kb

        if settings.DRY_RUN:
            return

        # Find users who activated this signal
        async with get_session() as session:
            result = await session.execute(
                select(UserSignalAction, User).join(
                    User, UserSignalAction.user_id == User.id
                ).where(UserSignalAction.signal_id == signal.id)
            )
            rows = result.all()

        if not rows:
            return

        # Map status to result type for image generation
        result_type_map = {
            SignalStatus.TP1_HIT: "tp1_hit",
            SignalStatus.TP2_HIT: "tp2_hit",
            SignalStatus.TP3_HIT: "tp3_hit",
            SignalStatus.STOPPED: "sl_hit",
            SignalStatus.CLOSED: "closed",
            SignalStatus.EXPIRED: "closed",
        }
        result_type = result_type_map.get(new_status, "closed")

        # Status headers for caption
        header_map = {
            SignalStatus.TP1_HIT: {"uk": "TP1 ДОСЯГНУТО!", "en": "TP1 HIT!", "ru": "TP1 ДОСТИГНУТ!"},
            SignalStatus.TP2_HIT: {"uk": "TP2 ДОСЯГНУТО!", "en": "TP2 HIT!", "ru": "TP2 ДОСТИГНУТ!"},
            SignalStatus.TP3_HIT: {"uk": "TP3 ДОСЯГНУТО! 🏆", "en": "TP3 HIT! 🏆", "ru": "TP3 ДОСТИГНУТ! 🏆"},
            SignalStatus.STOPPED: {"uk": "СТОП-ЛОСС", "en": "STOP LOSS", "ru": "СТОП-ЛОСС"},
            SignalStatus.CLOSED: {"uk": "СИГНАЛ ЗАКРИТО", "en": "SIGNAL CLOSED", "ru": "СИГНАЛ ЗАКРЫТ"},
            SignalStatus.EXPIRED: {"uk": "СИГНАЛ ЗАКРИТО", "en": "SIGNAL CLOSED", "ru": "СИГНАЛ ЗАКРЫТ"},
        }

        entry = signal.entry_actual or signal.entry_price
        pnl_str = f"{pnl:+.2f}%" if pnl is not None else "0.00%"

        # Generate result card per language
        img_by_lang: dict[str, bytes] = {}
        for lang in ("uk", "en", "ru"):
            try:
                img_by_lang[lang] = await generate_result_card(
                    coin_symbol=signal.coin_symbol,
                    direction=signal.direction.value,
                    result_type=result_type,
                    entry_price=entry,
                    exit_price=price,
                    pnl_pct=pnl or 0,
                    signal_id=signal.id,
                    lang=lang,
                )
            except Exception as e:
                logger.debug(f"Result card generation failed for lang={lang}: {e}")

        bot = Bot(token=settings.BOT_TOKEN)
        try:
            for action, user in rows:
                try:
                    lang = user.language.value
                    headers = header_map.get(new_status, header_map[SignalStatus.CLOSED])
                    header = headers.get(lang, headers["en"])

                    # Choose caption template
                    if is_final:
                        caption = t(
                            "signal_update_final_caption", lang,
                            header=header, coin=signal.coin_symbol,
                            signal_id=signal.id, pnl=pnl_str,
                        )
                    else:
                        caption = t(
                            "signal_update_tp_caption", lang,
                            header=header, coin=signal.coin_symbol,
                            signal_id=signal.id, pnl=pnl_str,
                        )

                    kb = signal_update_kb(signal.id, lang)

                    img = img_by_lang.get(lang)
                    if img:
                        photo = BufferedInputFile(img, filename=f"result_{signal.coin_symbol}.png")
                        await bot.send_photo(
                            chat_id=user.telegram_id,
                            photo=photo,
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                    else:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=caption,
                            parse_mode="HTML",
                            reply_markup=kb,
                        )
                except Exception:
                    pass  # User may have blocked the bot
        finally:
            await bot.session.close()

    async def _record_update(self, signal: Signal, update_type: UpdateType, price: float, details: dict):
        """Record a signal update event."""
        async with async_session() as session:
            update = SignalUpdate(
                signal_id=signal.id,
                update_type=update_type,
                price_at_update=price,
                details=details,
            )
            session.add(update)
            await session.commit()

    def _status_to_update_type(self, status: SignalStatus) -> UpdateType:
        mapping = {
            SignalStatus.TP1_HIT: UpdateType.TP1_HIT,
            SignalStatus.TP2_HIT: UpdateType.TP2_HIT,
            SignalStatus.TP3_HIT: UpdateType.TP3_HIT,
            SignalStatus.STOPPED: UpdateType.SL_HIT,
            SignalStatus.CLOSED: UpdateType.CLOSE,
            SignalStatus.CANCELLED: UpdateType.CANCEL,
            SignalStatus.EXPIRED: UpdateType.CLOSE,
        }
        return mapping.get(status, UpdateType.NOTE)


signal_tracker = SignalTracker()
