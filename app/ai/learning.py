"""
Self-learning and self-correction system.
Analyzes signal outcomes, identifies systematic errors, and adjusts parameters.
"""

import json
from datetime import datetime, timezone, timedelta
from loguru import logger
from sqlalchemy import select, func, and_

from app.database import async_session
from app.models import Signal, SignalStatus, AIFeedback, Tier
from app.ai.deepseek import deepseek
from app.ai.vectorstore import store_signal_outcome, store_memory


class SelfLearningEngine:
    """Monitors signal outcomes and self-corrects the system."""

    async def process_signal_outcome(self, signal_id: int):
        """Process a closed signal and learn from the outcome."""
        # Load signal fresh from DB to avoid detached object issues
        async with async_session() as session:
            result = await session.execute(
                select(Signal).where(Signal.id == signal_id)
            )
            signal = result.scalar_one_or_none()
        if not signal:
            logger.warning(f"Learning: signal #{signal_id} not found")
            return

        signal_data = {
            "id": signal.id,
            "coin_symbol": signal.coin_symbol,
            "direction": signal.direction.value,
            "exchange": signal.exchange,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "tp1": signal.tp1,
            "tp2": signal.tp2,
            "tp3": signal.tp3,
            "confidence_score": signal.confidence_score,
            "factors": signal.factors,
            "timeframe": signal.timeframe,
        }

        outcome_data = {
            "status": signal.status.value,
            "pnl_percent": signal.pnl_percent or 0,
            "max_drawdown": signal.max_drawdown_percent or 0,
            "peak_profit": signal.peak_profit_percent or 0,
            "entry_actual": signal.entry_actual,
            "exit_actual": signal.exit_actual,
            "duration_hours": (
                (signal.closed_at - signal.created_at).total_seconds() / 3600
                if signal.closed_at
                else None
            ),
        }

        # 1. Store outcome in vector memory for RAG
        await store_signal_outcome(signal_data, outcome_data)

        # 2. Determine feedback type CORRECTLY based on final status + actual results
        pnl = signal.pnl_percent or 0
        peak = signal.peak_profit_percent or 0

        if signal.status == SignalStatus.STOPPED:
            feedback_type = "stop_loss_hit"
        elif signal.status == SignalStatus.TP3_HIT:
            feedback_type = "target_hit"
        elif signal.status == SignalStatus.CLOSED:
            # CLOSED = post-TP1 SL hit or manual close
            # If PnL > 0, this was a partial win (TP1 was hit before SL)
            if pnl > 0:
                feedback_type = "partial_win"
            else:
                feedback_type = "stop_loss_after_entry"
        elif signal.status == SignalStatus.EXPIRED:
            # Expired can be: never entered, entered but no TP, or entered + partial TP
            if signal.entry_actual and peak > 0:
                feedback_type = "expired_with_profit"
            elif signal.entry_actual:
                feedback_type = "expired_after_entry"
            else:
                feedback_type = "expired_no_entry"
        else:
            feedback_type = "manual_close"

        # 3. Get recent feedback history
        async with async_session() as session:
            recent_feedback = await session.execute(
                select(AIFeedback)
                .where(AIFeedback.applied == False)
                .order_by(AIFeedback.created_at.desc())
                .limit(20)
            )
            history = [
                {"type": f.feedback_type, "context": f.context, "outcome": f.outcome}
                for f in recent_feedback.scalars().all()
            ]

        # 4. Ask AI for corrections
        corrections = await deepseek.self_correct_signal(signal_data, outcome_data, history)

        if not corrections or not corrections.get("lesson"):
            logger.warning(f"AI self-correction returned empty for signal #{signal.id}")
            return

        # 5. Store feedback
        lesson = corrections["lesson"]
        async with async_session() as session:
            feedback = AIFeedback(
                signal_id=signal.id,
                feedback_type=feedback_type,
                context=signal_data,
                outcome=outcome_data,
                lesson_learned=lesson,
                applied=False,
            )
            session.add(feedback)
            await session.commit()

        # 6. Store lesson in vector memory
        await store_memory(
            content=f"Lesson from {signal.coin_symbol} {signal.direction.value}: {lesson}",
            category="lesson_learned",
            metadata={
                "signal_id": signal.id,
                "feedback_type": feedback_type,
                "corrections": corrections,
            },
        )

        logger.info(f"Processed outcome for signal #{signal.id}: {feedback_type} — {lesson[:100]}")
        return corrections

    async def apply_accumulated_corrections(self):
        """Analyze accumulated feedback and apply systematic corrections."""
        from app.signals.engine import signal_engine

        async with async_session() as session:
            # Get unapplied feedback
            result = await session.execute(
                select(AIFeedback)
                .where(AIFeedback.applied == False)
                .order_by(AIFeedback.created_at.desc())
                .limit(50)
            )
            feedbacks = result.scalars().all()

        if len(feedbacks) < 5:
            logger.debug("Not enough feedback to apply corrections")
            return

        # Classify outcomes correctly
        losses = [f for f in feedbacks if f.feedback_type in ("stop_loss_hit", "stop_loss_after_entry")]
        wins = [f for f in feedbacks if f.feedback_type in ("target_hit", "partial_win", "expired_with_profit")]
        total_closed = len(losses) + len(wins)

        if total_closed == 0:
            return

        win_rate = len(wins) / total_closed
        applied_any = False

        logger.info(
            f"Self-correction analysis: {len(wins)}W / {len(losses)}L "
            f"({win_rate:.1%} WR) from {len(feedbacks)} feedbacks"
        )

        # ── Dynamic confidence threshold ──
        if win_rate < 0.45 and total_closed >= 10:
            old_min = signal_engine.MIN_CONFIDENCE
            signal_engine.MIN_CONFIDENCE = min(0.75, signal_engine.MIN_CONFIDENCE + 0.03)
            applied_any = True
            logger.warning(f"Raised MIN_CONFIDENCE: {old_min:.2f} → {signal_engine.MIN_CONFIDENCE:.2f}")

            await store_memory(
                content=f"Self-correction: raised MIN_CONFIDENCE {old_min:.2f} → {signal_engine.MIN_CONFIDENCE:.2f} due to {win_rate:.1%} win rate",
                category="system_adjustment",
                metadata={"old": old_min, "new": signal_engine.MIN_CONFIDENCE, "win_rate": win_rate},
            )
        elif win_rate > 0.70 and total_closed >= 10:
            old_min = signal_engine.MIN_CONFIDENCE
            signal_engine.MIN_CONFIDENCE = max(0.45, signal_engine.MIN_CONFIDENCE - 0.02)
            applied_any = True
            logger.info(f"Lowered MIN_CONFIDENCE: {old_min:.2f} → {signal_engine.MIN_CONFIDENCE:.2f}")

            await store_memory(
                content=f"Self-correction: lowered MIN_CONFIDENCE {old_min:.2f} → {signal_engine.MIN_CONFIDENCE:.2f} due to {win_rate:.1%} win rate",
                category="system_adjustment",
                metadata={"old": old_min, "new": signal_engine.MIN_CONFIDENCE, "win_rate": win_rate},
            )

        # ── Aggregate AI correction recommendations ──
        sl_factors = []
        tp_factors = []
        avoid_patterns = []
        prefer_patterns = []

        for f in feedbacks:
            if not f.lesson_learned:
                continue
            # Try to find stored corrections in vector memory metadata
            # The corrections dict was stored in the lesson's metadata
            try:
                async with async_session() as session:
                    from app.models import VectorMemory
                    mem_result = await session.execute(
                        select(VectorMemory).where(
                            and_(
                                VectorMemory.category == "lesson_learned",
                                VectorMemory.metadata_["signal_id"].as_integer() == f.signal_id,
                            )
                        ).limit(1)
                    )
                    memory = mem_result.scalar_one_or_none()
                    if memory and memory.metadata_:
                        corrections = memory.metadata_.get("corrections", {})
                        sl_adj = corrections.get("sl_adjustment_factor")
                        tp_adj = corrections.get("tp_adjustment_factor")
                        if sl_adj and 0.8 <= sl_adj <= 1.2:
                            sl_factors.append(sl_adj)
                        if tp_adj and 0.8 <= tp_adj <= 1.2:
                            tp_factors.append(tp_adj)
                        avoid_patterns.extend(corrections.get("avoid_patterns", []))
                        prefer_patterns.extend(corrections.get("prefer_patterns", []))
            except Exception:
                continue

        # Apply aggregate SL/TP adjustments if consistent trend
        if len(sl_factors) >= 3:
            avg_sl = sum(sl_factors) / len(sl_factors)
            if abs(avg_sl - 1.0) > 0.03:  # Only act on meaningful deviation
                applied_any = True
                logger.info(f"AI suggests SL adjustment factor: {avg_sl:.3f} (from {len(sl_factors)} signals)")
                await store_memory(
                    content=f"Aggregate SL adjustment recommendation: {avg_sl:.3f}x from {len(sl_factors)} analyzed signals",
                    category="system_adjustment",
                    metadata={"sl_factor": avg_sl, "sample_size": len(sl_factors)},
                )

        if len(tp_factors) >= 3:
            avg_tp = sum(tp_factors) / len(tp_factors)
            if abs(avg_tp - 1.0) > 0.03:
                applied_any = True
                logger.info(f"AI suggests TP adjustment factor: {avg_tp:.3f} (from {len(tp_factors)} signals)")
                await store_memory(
                    content=f"Aggregate TP adjustment recommendation: {avg_tp:.3f}x from {len(tp_factors)} analyzed signals",
                    category="system_adjustment",
                    metadata={"tp_factor": avg_tp, "sample_size": len(tp_factors)},
                )

        # Log pattern insights
        if avoid_patterns:
            from collections import Counter
            top_avoid = Counter(avoid_patterns).most_common(5)
            logger.info(f"Patterns to avoid: {top_avoid}")
            await store_memory(
                content=f"Patterns correlated with losses: {top_avoid}",
                category="pattern_insight",
                metadata={"avoid": top_avoid, "sample": len(feedbacks)},
            )
            applied_any = True

        if prefer_patterns:
            from collections import Counter
            top_prefer = Counter(prefer_patterns).most_common(5)
            logger.info(f"Patterns to prefer: {top_prefer}")
            await store_memory(
                content=f"Patterns correlated with wins: {top_prefer}",
                category="pattern_insight",
                metadata={"prefer": top_prefer, "sample": len(feedbacks)},
            )
            applied_any = True

        # ── Analyze SL effectiveness ──
        sl_too_tight = 0
        for f in losses:
            outcome = f.outcome or {}
            if outcome.get("peak_profit", 0) > 0 and outcome.get("peak_profit", 0) > abs(outcome.get("pnl_percent", 0)) * 0.5:
                sl_too_tight += 1

        if sl_too_tight > len(losses) * 0.4 and len(losses) >= 5:
            applied_any = True
            logger.warning(f"SL too tight: {sl_too_tight}/{len(losses)} SL hits had significant interim profit")
            await store_memory(
                content=f"Pattern detected: {sl_too_tight}/{len(losses)} SL hits had significant interim profit. SLs are too tight.",
                category="system_adjustment",
                metadata={"sl_too_tight_count": sl_too_tight, "total_sl": len(losses)},
            )

        # Only mark as applied if we actually analyzed and acted
        if applied_any or total_closed >= 10:
            async with async_session() as session:
                feedback_ids = [f.id for f in feedbacks]
                result = await session.execute(
                    select(AIFeedback).where(AIFeedback.id.in_(feedback_ids))
                )
                for fb in result.scalars().all():
                    fb.applied = True
                await session.commit()
            logger.info(f"Marked {len(feedbacks)} feedbacks as applied")
        else:
            logger.debug("No corrections applied, keeping feedbacks for next cycle")

    async def get_system_health(self) -> dict:
        """Get current system performance metrics for monitoring."""
        from app.signals.engine import signal_engine

        async with async_session() as session:
            # Last 7 days stats
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            total = await session.scalar(
                select(func.count(Signal.id)).where(Signal.created_at >= week_ago)
            )
            # Wins = TP hits + CLOSED with positive PnL (partial wins)
            tp_wins = await session.scalar(
                select(func.count(Signal.id)).where(
                    and_(
                        Signal.created_at >= week_ago,
                        Signal.status.in_([SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT]),
                    )
                )
            ) or 0
            partial_wins = await session.scalar(
                select(func.count(Signal.id)).where(
                    and_(
                        Signal.created_at >= week_ago,
                        Signal.status == SignalStatus.CLOSED,
                        Signal.pnl_percent > 0,
                    )
                )
            ) or 0
            wins = tp_wins + partial_wins

            # Losses = STOPPED + CLOSED with negative PnL
            stopped = await session.scalar(
                select(func.count(Signal.id)).where(
                    and_(Signal.created_at >= week_ago, Signal.status == SignalStatus.STOPPED)
                )
            ) or 0
            closed_losses = await session.scalar(
                select(func.count(Signal.id)).where(
                    and_(
                        Signal.created_at >= week_ago,
                        Signal.status == SignalStatus.CLOSED,
                        Signal.pnl_percent <= 0,
                    )
                )
            ) or 0
            losses = stopped + closed_losses
            active = await session.scalar(
                select(func.count(Signal.id)).where(Signal.status == SignalStatus.ACTIVE)
            )
            avg_pnl = await session.scalar(
                select(func.avg(Signal.pnl_percent)).where(
                    and_(Signal.created_at >= week_ago, Signal.pnl_percent.isnot(None))
                )
            )

        closed = (wins or 0) + (losses or 0)
        return {
            "period": "7d",
            "total_signals": total or 0,
            "active": active or 0,
            "wins": wins or 0,
            "losses": losses or 0,
            "win_rate": round((wins or 0) / closed * 100, 1) if closed > 0 else 0,
            "avg_pnl": round(avg_pnl or 0, 2),
            "min_confidence": round(signal_engine.MIN_CONFIDENCE, 2),
        }


self_learning = SelfLearningEngine()
