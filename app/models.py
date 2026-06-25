import enum
import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean,
    Date, DateTime, Text, ForeignKey, Index, Enum as SAEnum,
    JSON, func, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base


# ─── Enums ────────────────────────────────────────────────

class Language(str, enum.Enum):
    UK = "uk"
    EN = "en"
    RU = "ru"
    AR = "ar"


class Tier(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"


class SignalDirection(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class SignalStatus(str, enum.Enum):
    ACTIVE = "active"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    STOPPED = "stopped"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class UpdateType(str, enum.Enum):
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    SL_HIT = "sl_hit"
    ENTRY_HIT = "entry_hit"
    ADJUSTMENT = "adjustment"
    CLOSE = "close"
    CANCEL = "cancel"
    NOTE = "note"


# ─── Models ───────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[Language] = mapped_column(SAEnum(Language), default=Language.EN, nullable=False)
    tier: Mapped[Tier] = mapped_column(SAEnum(Tier), default=Tier.FREE, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    subscriptions = relationship("Subscription", back_populates="user", lazy="selectin")
    payments = relationship("Payment", back_populates="user", lazy="selectin")

    @property
    def subscription_expires_at(self) -> datetime.datetime | None:
        """Returns the expiration date of the latest active subscription."""
        now = datetime.datetime.now(datetime.timezone.utc)
        active_subs = [s for s in self.subscriptions if s.is_active and s.expires_at > now]
        if not active_subs:
            return None
        return max(s.expires_at for s in active_subs)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    coin_name: Mapped[str] = mapped_column(String(100), nullable=False)
    coin_logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    pair: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(SAEnum(SignalDirection), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="4h")

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    entry_zone_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    tp1: Mapped[float] = mapped_column(Float, nullable=False)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)

    leverage_suggested: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[SignalStatus] = mapped_column(
        SAEnum(SignalStatus), default=SignalStatus.ACTIVE, nullable=False, index=True
    )

    # Actual results
    entry_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_profit_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Analysis factors that triggered the signal
    factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tier visibility
    min_tier: Mapped[Tier] = mapped_column(SAEnum(Tier), default=Tier.FREE, nullable=False)

    # Telegram message IDs per channel (to edit later)
    message_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updates = relationship("SignalUpdate", back_populates="signal", lazy="selectin", order_by="SignalUpdate.created_at")

    __table_args__ = (
        Index("ix_signals_status_created", "status", "created_at"),
        Index("ix_signals_coin_status", "coin_symbol", "status"),
    )


class SignalUpdate(Base):
    __tablename__ = "signal_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(Integer, ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    update_type: Mapped[UpdateType] = mapped_column(SAEnum(UpdateType), nullable=False)
    price_at_update: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    message_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    signal = relationship("Signal", back_populates="updates")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tier: Mapped[Tier] = mapped_column(SAEnum(Tier), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payments.id"), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="subscriptions")
    payment = relationship("Payment", back_populates="subscription")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nowpayments_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    order_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    pay_currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pay_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    months: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    invoice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payment", uselist=False)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    coins_mentioned: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_news_created_processed", "created_at", "is_processed"),
    )


class VectorMemory(Base):
    __tablename__ = "vector_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    embedding = Column(Vector(1536), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("signals.id", ondelete="SET NULL"), nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)  # signal_accuracy, prediction_error, etc.
    context: Mapped[dict] = mapped_column(JSON, nullable=False)
    outcome: Mapped[dict] = mapped_column(JSON, nullable=False)
    lesson_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_feedback_type_applied", "feedback_type", "applied"),
    )


class MarketSnapshot(Base):
    """Periodic market state snapshots for correlation and analysis."""
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_1h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_change_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_snapshot_coin_time", "coin_symbol", "created_at"),
    )


# ─── Historical Candles (OHLCV) ──────────────────────────

class CandleTimeframe(str, enum.Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class CandleRecord(Base):
    """Normalized OHLCV candle data from all exchanges."""
    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[CandleTimeframe] = mapped_column(SAEnum(CandleTimeframe), nullable=False)
    open_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("coin_symbol", "exchange", "timeframe", "open_time", name="uq_candle"),
        Index("ix_candle_lookup", "coin_symbol", "exchange", "timeframe", "open_time"),
        Index("ix_candle_time", "open_time"),
    )


class CoinMeta(Base):
    """Coin metadata + CoinGecko enrichment (logo, market cap, supply, etc.)."""
    __tablename__ = "coin_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    coingecko_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_thumb_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_supply: Mapped[float | None] = mapped_column(Float, nullable=True)
    circulating_supply: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_supply: Mapped[float | None] = mapped_column(Float, nullable=True)
    ath: Mapped[float | None] = mapped_column(Float, nullable=True)
    ath_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    atl: Mapped[float | None] = mapped_column(Float, nullable=True)
    atl_date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    categories: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchanges_available: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DailyAIAnalysis(Base):
    """Daily AI market analysis for top coins."""
    __tablename__ = "daily_ai_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    coin_symbol: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # market_overview, coin_analysis, trend_report
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_daily_ai_date_type", "date", "analysis_type"),
        Index("ix_daily_ai_coin_date", "coin_symbol", "date"),
    )


# ─── Alert System Enums & Models ─────────────────────────

class AlertType(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    CHANGE_1H = "change_1h"
    CHANGE_24H = "change_24h"
    VOLUME_SPIKE = "volume_spike"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    MACD_CROSS = "macd_cross"
    BB_BREAKOUT = "bb_breakout"
    NEW_ATH = "new_ath"
    NEW_ATL = "new_atl"
    FUNDING_RATE = "funding_rate"
    CORRELATION_BREAK = "correlation_break"
    SUPPORT_HIT = "support_hit"
    RESISTANCE_HIT = "resistance_hit"
    CUSTOM_RANGE = "custom_range"


class UserAlert(Base):
    """User-configured price/indicator alert."""
    __tablename__ = "user_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_alerts_user_active", "user_id", "is_active"),
        Index("ix_alerts_coin_active", "coin_symbol", "is_active"),
    )


class AlertLog(Base):
    """Log of triggered alerts for audit and analytics."""
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_alerts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), nullable=False)
    trigger_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserWatchlist(Base):
    """User's bookmarked coins for tracking and alerts."""
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coin_symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "coin_symbol", name="uq_user_coin"),
    )


class UserApiKey(Base):
    """Per-user API key for desktop/external app access."""
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # first 8 chars for identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Desktop App")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_apikeys_user_active", "user_id", "is_active"),
    )


# ─── Wallet Tracker ──────────────────────────────────────

class ChainType(str, enum.Enum):
    ETHEREUM = "ethereum"
    BSC = "bsc"
    ARBITRUM = "arbitrum"
    BASE = "base"
    POLYGON = "polygon"
    SOLANA = "solana"
    TRON = "tron"


class TrackedWallet(Base):
    """User-tracked blockchain wallet."""
    __tablename__ = "tracked_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    chain: Mapped[ChainType] = mapped_column(SAEnum(ChainType), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cached portfolio value (updated each poll)
    total_value_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    native_balance: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_scanned_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Alerts configuration (JSON: {new_tx: true, large_transfer_usd: 1000, new_token: true})
    alert_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tokens = relationship("WalletToken", back_populates="wallet", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "address", "chain", name="uq_user_wallet_chain"),
        Index("ix_wallet_user_active", "user_id", "is_active"),
        Index("ix_wallet_chain_active", "chain", "is_active"),
    )


class WalletToken(Base):
    """Token balance in a tracked wallet."""
    __tablename__ = "wallet_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("tracked_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_address: Mapped[str | None] = mapped_column(String(128), nullable=True)  # None = native token
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    decimals: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    balance_raw: Mapped[str] = mapped_column(String(78), nullable=False, default="0")  # uint256 as string
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    wallet = relationship("TrackedWallet", back_populates="tokens")

    __table_args__ = (
        UniqueConstraint("wallet_id", "contract_address", name="uq_wallet_token"),
        Index("ix_wtoken_wallet", "wallet_id"),
    )


class WalletTransaction(Base):
    """Transaction recorded for a tracked wallet."""
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("tracked_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    chain: Mapped[ChainType] = mapped_column(SAEnum(ChainType), nullable=False)
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    from_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # tx classification
    tx_type: Mapped[str] = mapped_column(String(30), nullable=False, default="transfer")  # transfer, swap, approve, contract, receive
    token_symbol: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # For swaps: what was received
    token_out_symbol: Mapped[str | None] = mapped_column(String(30), nullable=True)
    amount_out: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_out_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("wallet_id", "tx_hash", name="uq_wallet_tx"),
        Index("ix_wtx_wallet_time", "wallet_id", "timestamp"),
        Index("ix_wtx_chain", "chain"),
    )


# ─── Signal Tracking (User ↔ Signal) ─────────────────────

class UserSignalAction(Base):
    """Tracks users who activated a signal ('Use Signal' button).

    Stores bot DM message_id so we can edit/update the notification later
    when TP/SL hits occur.
    """
    __tablename__ = "user_signal_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    signal_id: Mapped[int] = mapped_column(Integer, ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)

    # Bot DM message ID (for editing later with updates)
    bot_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Notification message ID for the original signal notification
    notification_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "signal_id", name="uq_user_signal_action"),
        Index("ix_usa_signal", "signal_id"),
        Index("ix_usa_user", "user_id"),
    )
