"""
RAG (Retrieval Augmented Generation) for enriched AI analysis.
Combines vector memory search with DeepSeek AI for context-aware decisions.
"""

import json
from loguru import logger

from app.ai.deepseek import deepseek
from app.ai.vectorstore import (
    get_relevant_history,
    get_similar_market_conditions,
    get_relevant_lessons,
    search_memory,
)
from app.data.news_parser import news_parser
from app.database import async_session
from app.models import NewsItem
from sqlalchemy import select, desc


class RAGEngine:
    """Retrieval Augmented Generation engine for signal analysis."""

    async def enrich_signal_analysis(
        self,
        coin_symbol: str,
        direction: str,
        indicators: dict,
        confidence: float,
        lang: str = "en",
    ) -> dict:
        """Full RAG pipeline: retrieve context → augment → generate enhanced analysis."""

        # 1. Retrieve similar past signals and their outcomes
        history = await get_relevant_history(coin_symbol, direction, limit=5)

        # 2. Get similar market conditions (searches signal_outcome with indicator context)
        indicators_str = (
            f"RSI: {indicators.get('rsi_14')}, MACD: {indicators.get('macd_histogram')}, "
            f"Volume ratio: {indicators.get('volume_ratio')}, ADX: {indicators.get('adx')}, "
            f"ATR%: {indicators.get('atr_percent')}, {direction} signal"
        )
        similar_conditions = await get_similar_market_conditions(indicators_str, limit=3)

        # 3. Get recent news about this coin
        recent_news = await self._get_recent_news(coin_symbol)

        # 4. Get overall market sentiment memories
        market_sentiment = await search_memory(
            "crypto market sentiment fear greed trend", category="market_context", limit=2
        )

        # 5. Get lessons learned from past trades
        lessons = await get_relevant_lessons(coin_symbol, direction, limit=3)

        # 5. Build enhanced context for AI
        context_parts = []

        if history:
            context_parts.append("**Past signals for this coin:**")
            for h in history:
                context_parts.append(f"  - {h['content']} (similarity: {h['similarity']:.2f})")

        if similar_conditions:
            context_parts.append("\n**Similar market conditions in the past:**")
            for sc in similar_conditions:
                context_parts.append(f"  - {sc['content']} (similarity: {sc['similarity']:.2f})")

        if recent_news:
            context_parts.append("\n**Recent news:**")
            for n in recent_news:
                context_parts.append(f"  - [{n['source']}] {n['title']}")

        if market_sentiment:
            context_parts.append("\n**Market sentiment context:**")
            for ms in market_sentiment:
                context_parts.append(f"  - {ms['content'][:200]}")

        if lessons:
            context_parts.append("\n**Lessons from past trades:**")
            for ls in lessons:
                context_parts.append(f"  - {ls['content'][:300]} (similarity: {ls['similarity']:.2f})")

        context = "\n".join(context_parts) if context_parts else "No historical context available."

        # 6. AI-enhanced analysis with full context
        analysis = await self._generate_rag_analysis(
            coin_symbol=coin_symbol,
            direction=direction,
            indicators=indicators,
            confidence=confidence,
            context=context,
            lang=lang,
        )

        # 7. Compute confidence adjustment based on historical success rate
        historical_adjustment = self._compute_historical_adjustment(history, direction)

        analysis["historical_context"] = {
            "similar_signals_found": len(history),
            "similar_conditions_found": len(similar_conditions),
            "news_items": len(recent_news),
            "historical_confidence_adjustment": historical_adjustment,
        }

        analysis["confidence_adjustment"] = (
            analysis.get("confidence_adjustment", 0)
            + historical_adjustment
        )

        return analysis

    async def _get_recent_news(self, coin_symbol: str, limit: int = 5) -> list[dict]:
        """Get recent news articles relevant to the coin."""
        async with async_session() as session:
            stmt = (
                select(NewsItem)
                .where(NewsItem.is_processed == True)
                .order_by(desc(NewsItem.created_at))
                .limit(50)
            )
            result = await session.execute(stmt)
            news_items = result.scalars().all()

        # Filter by coin mention
        relevant = []
        symbol_lower = coin_symbol.lower()
        for item in news_items:
            coins = item.coins_mentioned or []
            if symbol_lower in [c.lower() for c in coins]:
                relevant.append({
                    "source": item.source,
                    "title": item.title,
                    "sentiment": item.sentiment,
                    "importance": item.importance_score,
                })
            elif symbol_lower in item.title.lower():
                relevant.append({
                    "source": item.source,
                    "title": item.title,
                    "sentiment": item.sentiment,
                    "importance": item.importance_score,
                })

        return relevant[:limit]

    async def _generate_rag_analysis(
        self,
        coin_symbol: str,
        direction: str,
        indicators: dict,
        confidence: float,
        context: str,
        lang: str = "en",
    ) -> dict:
        """Generate AI analysis enriched with RAG context."""
        prompt = f"""You are a crypto trading AI that enriches signals with historical context.

**Current signal:** {direction.upper()} {coin_symbol}
**Current confidence:** {confidence:.0f}%
**Indicators:** {json.dumps(indicators, indent=2, default=str)}

**Historical Context (retrieved from memory):**
{context}

IMPORTANT INSTRUCTIONS:
- Focus on the CURRENT signal's technical quality first. Historical data is supplementary.
- Old losing signals may reflect an OLDER version of the system — DO NOT over-penalize based on old losses.
- If historical data is sparse or low-similarity (<0.7), treat it as weak evidence and stay close to 0.
- Use the FULL range from -0.12 to +0.12. Don't default to slightly negative.
- Positive adjustment: strong current technicals + positive or neutral history.
- Negative adjustment: clear technical weakness confirmed by historical losses.
- Near zero: mixed signals or insufficient historical data.

Based on your analysis of both current technical data AND historical context:
1. Should the confidence be adjusted up or down?
2. What patterns from history are relevant?
3. What risks does the historical context reveal?

Respond in JSON:
{{
    "confidence_adjustment": <float between -0.12 and +0.12>,
    "reasoning_en": "<analysis in English, 2-3 sentences>",
    "reasoning_uk": "<аналіз Українською, 2-3 речення>",
    "reasoning_ru": "<анализ на Русском, 2-3 предложения>",
    "relevant_historical_pattern": "<what historical pattern is most relevant>",
    "risk_from_history": "<risk identified from past similar trades>"
}}"""

        try:
            response = await deepseek.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"RAG analysis failed: {e}")
            return {
                "confidence_adjustment": 0.0,
                "reasoning_en": "RAG analysis unavailable",
                "reasoning_uk": "RAG аналіз недоступний",
                "reasoning_ru": "RAG анализ недоступен",
            }

    def _compute_historical_adjustment(self, history: list[dict], direction: str) -> float:
        """Compute confidence adjustment based on past outcomes, weighted by similarity and recency."""
        if not history:
            return 0.0

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        weighted_wins = 0.0
        weighted_losses = 0.0
        for h in history:
            meta = h.get("metadata", {})
            similarity = h.get("similarity", 0.5)  # cosine similarity 0-1

            # Recency decay: signals older than 14 days get reduced weight
            recency_weight = 1.0
            created = h.get("created_at")
            if created:
                try:
                    if isinstance(created, str):
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        created_dt = created
                    age_days = (now - created_dt).total_seconds() / 86400
                    if age_days > 30:
                        recency_weight = 0.1  # very old signals almost ignored
                    elif age_days > 14:
                        recency_weight = 0.4
                    elif age_days > 7:
                        recency_weight = 0.7
                except Exception:
                    recency_weight = 0.3  # unknown age — discount

            weight = similarity * recency_weight

            if meta.get("direction") == direction:
                pnl = meta.get("pnl", 0)
                if pnl and pnl > 0:
                    weighted_wins += weight
                elif pnl and pnl < 0:
                    weighted_losses += weight

        total = weighted_wins + weighted_losses
        if total < 1.0:  # Not enough confident matches
            return 0.0

        win_rate = weighted_wins / total
        # Positive adjustment for >60% historical win rate, negative for <40%
        if win_rate > 0.7:
            return 0.10
        elif win_rate > 0.6:
            return 0.05
        elif win_rate < 0.3:
            return -0.10
        elif win_rate < 0.4:
            return -0.05
        return 0.0


rag_engine = RAGEngine()
