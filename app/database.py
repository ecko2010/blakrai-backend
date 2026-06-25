from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from loguru import logger


engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    from app.models import (
        User, Signal, SignalUpdate, Subscription,
        Payment, NewsItem, VectorMemory, AIFeedback,
        MarketSnapshot, UserAlert, AlertLog, UserWatchlist,
        UserApiKey, CandleRecord, CoinMeta, DailyAIAnalysis,
    )
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db():
    await engine.dispose()
    logger.info("Database connections closed")
