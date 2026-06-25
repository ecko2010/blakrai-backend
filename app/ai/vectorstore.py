"""
Vector store using pgvector for RAG memory.
Stores signal outcomes, lessons, market contexts for retrieval.
"""

import json
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import async_session
from app.models import VectorMemory
from app.ai.deepseek import deepseek


# ─── OpenAI embedding client (singleton) ─────────────
_embedding_client: "AsyncOpenAI | None" = None


def _get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        import httpx
        from openai import AsyncOpenAI
        from app.config import settings
        _embedding_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=httpx.AsyncClient(
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                timeout=httpx.Timeout(30.0),
            ),
        )
    return _embedding_client


async def get_embedding(text_content: str) -> list[float]:
    """Generate embedding using OpenAI text-embedding-3-small (1536-dim)."""
    from app.config import settings
    client = _get_embedding_client()
    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text_content[:8000],
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"OpenAI embedding failed: {e}")
        # Last-resort fallback: deterministic hash (NOT semantic — only for dev/testing)
        import hashlib
        embedding = []
        for i in range(24):
            seed = hashlib.sha512(f"{text_content}:{i}".encode()).digest()
            for byte in seed:
                embedding.append((byte - 128) / 128.0)
        return embedding[:1536]


async def store_memory(
    content: str,
    category: str,
    metadata: dict | None = None,
) -> int:
    """Store a new memory with its embedding."""
    embedding = await get_embedding(content)

    async with async_session() as session:
        memory = VectorMemory(
            content=content,
            metadata_=metadata or {},
            category=category,
            embedding=embedding,
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory.id


async def search_memory(
    query: str,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search memories by semantic similarity using pgvector."""
    query_embedding = await get_embedding(query)

    async with async_session() as session:
        # Use pgvector cosine distance operator
        distance_expr = VectorMemory.embedding.cosine_distance(query_embedding)

        stmt = select(
            VectorMemory.id,
            VectorMemory.content,
            VectorMemory.metadata_,
            VectorMemory.category,
            VectorMemory.created_at,
            distance_expr.label("distance"),
        )

        if category:
            stmt = stmt.where(VectorMemory.category == category)

        stmt = stmt.order_by(distance_expr).limit(limit)
        result = await session.execute(stmt)

        memories = []
        for row in result:
            memories.append({
                "id": row.id,
                "content": row.content,
                "metadata": row.metadata_,
                "category": row.category,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "similarity": round(1 - row.distance, 4),  # Convert distance to similarity
            })
        return memories


async def store_signal_outcome(signal_data: dict, outcome_data: dict):
    """Store signal outcome as a learning memory with FULL technical context."""
    factors = signal_data.get("factors", {})
    indicators = factors.get("indicators", {})
    regime = factors.get("regime", {})
    patterns = factors.get("patterns", {})

    # Build a rich content string that captures the technical conditions
    # so that embedding similarity actually works on technical similarity
    pattern_strs = []
    for tf, pats in patterns.items():
        if pats:
            pattern_strs.append(f"{tf}: {', '.join(pats)}")

    content = (
        f"Signal {signal_data.get('direction', '')} {signal_data.get('coin_symbol', '')} "
        f"on {signal_data.get('exchange', '')}. "
        f"TF: {signal_data.get('timeframe', 'unknown')}. "
        f"Entry: {signal_data.get('entry_price')}, SL: {signal_data.get('stop_loss')}, "
        f"TP1: {signal_data.get('tp1')}. "
        f"Result: {outcome_data.get('status', '')} with PnL {outcome_data.get('pnl_percent', 0):.2f}%. "
        f"Peak profit: {outcome_data.get('peak_profit', 0):.2f}%, Max DD: {outcome_data.get('max_drawdown', 0):.2f}%. "
        f"Confidence was {signal_data.get('confidence_score', 0):.0f}%. "
        f"RSI: {indicators.get('rsi_14', 'N/A')}, MACD: {indicators.get('macd_histogram', 'N/A')}, "
        f"ADX: {indicators.get('adx', 'N/A')}, Volume ratio: {indicators.get('volume_ratio', 'N/A')}, "
        f"ATR%: {indicators.get('atr_percent', 'N/A')}. "
        f"Regime: {regime.get('type', 'unknown')} (strength {regime.get('strength', 0)}). "
        f"Trends: {json.dumps(factors.get('trend', {}), default=str)}. "
        f"Patterns: {'; '.join(pattern_strs) if pattern_strs else 'None'}."
    )

    await store_memory(
        content=content,
        category="signal_outcome",
        metadata={
            "signal_id": signal_data.get("id"),
            "coin": signal_data.get("coin_symbol"),
            "direction": signal_data.get("direction"),
            "pnl": outcome_data.get("pnl_percent"),
            "peak_profit": outcome_data.get("peak_profit"),
            "max_drawdown": outcome_data.get("max_drawdown"),
            "status": outcome_data.get("status"),
            "confidence": signal_data.get("confidence_score"),
            "rsi": indicators.get("rsi_14"),
            "adx": indicators.get("adx"),
            "volume_ratio": indicators.get("volume_ratio"),
            "regime": regime.get("type"),
            "timeframe": signal_data.get("timeframe"),
        },
    )


async def store_market_context(context_summary: str, metadata: dict | None = None):
    """Store a market context snapshot for future reference."""
    await store_memory(
        content=context_summary,
        category="market_context",
        metadata=metadata,
    )


async def get_relevant_history(coin_symbol: str, direction: str, limit: int = 5) -> list[dict]:
    """Get relevant past signal outcomes for a coin/direction combo."""
    query = f"Signal {direction} {coin_symbol} outcome result"
    return await search_memory(query, category="signal_outcome", limit=limit)


async def get_similar_market_conditions(indicators_summary: str, limit: int = 3) -> list[dict]:
    """Find similar past signal conditions (not just market snapshots).
    Searches signal_outcome category because those contain full technical indicators."""
    return await search_memory(indicators_summary, category="signal_outcome", limit=limit)


async def get_relevant_lessons(coin_symbol: str, direction: str, limit: int = 3) -> list[dict]:
    """Get lessons learned from past similar trade outcomes."""
    query = f"Lesson {direction} {coin_symbol} loss win pattern"
    return await search_memory(query, category="lesson_learned", limit=limit)
