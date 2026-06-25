from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_UK_FREE: int = 0
    TELEGRAM_CHANNEL_UK_PRO: int = 0
    TELEGRAM_CHANNEL_EN_FREE: int = 0
    TELEGRAM_CHANNEL_EN_PRO: int = 0
    TELEGRAM_CHANNEL_RU_FREE: int = 0
    TELEGRAM_CHANNEL_RU_PRO: int = 0
    TELEGRAM_CHANNEL_AR_FREE: int = 0
    TELEGRAM_CHANNEL_AR_PRO: int = 0
    TELEGRAM_ADMIN_IDS: str = ""
    BOT_USERNAME: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/blaksignals"

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to asyncpg format.

        Railway provides postgresql:// but SQLAlchemy async needs postgresql+asyncpg://.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI (for embeddings)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Exchanges
    BINANCE_BASE_URL: str = "https://api.binance.com"
    BYBIT_BASE_URL: str = "https://api.bybit.com"
    OKX_BASE_URL: str = "https://www.okx.com"
    KUCOIN_BASE_URL: str = "https://api.kucoin.com"
    GATEIO_BASE_URL: str = "https://api.gateio.ws"
    MEXC_BASE_URL: str = "https://api.mexc.com"
    BITGET_BASE_URL: str = "https://api.bitget.com"
    HTX_BASE_URL: str = "https://api.huobi.pro"

    # CoinGecko
    COINGECKO_API_KEY: str = ""
    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"

    # DexScreener
    DEXSCREENER_BASE_URL: str = "https://api.dexscreener.com/latest"

    # NOWPayments
    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""
    NOWPAYMENTS_BASE_URL: str = "https://api.nowpayments.io/v1"
    NOWPAYMENTS_IPN_URL: str = ""

    # Pricing
    PRICE_PRO_MONTHLY: float = 29.00
    PRICE_PRO_YEARLY: float = 249.00
    PRICE_ELITE_MONTHLY: float = 99.00
    PRICE_ELITE_YEARLY: float = 849.00

    # App
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"

    # Admin API
    ADMIN_API_KEY: str = ""

    # Admin Panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    ADMIN_SECRET_KEY: str = "change-me-in-production"

    # Test mode — signals generated & tracked but NOT published to channels
    DRY_RUN: bool = False

    # ─── Wallet Tracker ──────────────────────────────
    ALCHEMY_API_KEY: str = ""
    HELIUS_API_KEY: str = ""
    WALLET_POLL_INTERVAL_SECONDS: int = 60

    @property
    def admin_ids(self) -> List[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(",") if x.strip()]

    @property
    def BOT_TOKEN(self) -> str:
        return self.TELEGRAM_BOT_TOKEN

    def get_channel_id(self, lang: str, tier: str) -> int:
        """Return channel ID for language × tier combination.

        tier should be 'free' or 'pro'. ELITE users go to the PRO channel.
        """
        is_pro = tier in ("pro", "elite")
        key = f"TELEGRAM_CHANNEL_{lang.upper()}_{'PRO' if is_pro else 'FREE'}"
        return getattr(self, key, 0)

    @property
    def all_channel_ids(self) -> dict[str, int]:
        """Return mapping {label: channel_id} for all configured channels."""
        channels = {}
        for lang in ("uk", "en", "ru", "ar"):
            for tier in ("free", "pro"):
                cid = self.get_channel_id(lang, tier)
                if cid:
                    channels[f"{lang}_{tier}"] = cid
        return channels

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
