"""
Base exchange interface.
All exchange adapters must implement this protocol.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import datetime
import httpx


class ExchangeError(Exception):
    """Raised when an exchange API call fails."""
    pass


@dataclass
class OHLCV:
    timestamp: datetime.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# Alias for modules that use Candle convention
@dataclass
class Candle:
    timestamp: datetime.datetime
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass
class Ticker:
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    price_change_24h: float
    price_change_pct_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime.datetime | None = None


@dataclass
class OrderBookLevel:
    price: float
    quantity: float


@dataclass
class OrderBook:
    bids: list  # list[tuple[float, float]] or list[OrderBookLevel]
    asks: list
    symbol: str = ""
    timestamp: datetime.datetime | None = None


@dataclass
class FundingRate:
    symbol: str
    rate: float
    next_funding_time: datetime.datetime | None = None


@dataclass
class OpenInterest:
    symbol: str
    open_interest: float
    open_interest_value: float | None = None


class BaseExchange(ABC):
    """Abstract base for all exchange adapters."""

    name: str = "base"

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        ...

    @abstractmethod
    async def get_klines(
        self, symbol: str, interval: str = "4h", limit: int = 200
    ) -> list[OHLCV]:
        """Return candle data. Subclasses may override get_candles() instead."""
        ...

    async def get_candles(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[Candle]:
        """Get candles — default converts from get_klines(). Override for native support."""
        ohlcvs = await self.get_klines(symbol, interval, limit)
        return [
            Candle(timestamp=o.timestamp, o=o.open, h=o.high, l=o.low, c=o.close, v=o.volume)
            for o in ohlcvs
        ]

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        ...

    @abstractmethod
    async def get_all_tickers(self) -> list[Ticker]:
        ...

    async def close(self):
        """Close HTTP client. Override if needed."""
        if hasattr(self, "_client") and self._client:
            await self._client.aclose()

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        ...

    @abstractmethod
    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        ...

    @abstractmethod
    async def get_symbols(self) -> list[str]:
        ...
