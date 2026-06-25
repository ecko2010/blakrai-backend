"""
Unified CCXT exchange adapter — replaces 8 custom adapters with one implementation.
Public data only, no API keys required.
"""

import asyncio
import datetime
import time

import ccxt.async_support as ccxt_async
from loguru import logger

from app.exchanges.base import (
    BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError,
)

# Map our exchange IDs to CCXT exchange IDs where they differ
CCXT_ID_MAP = {
    "gateio": "gate",
}

# Proper display names
DISPLAY_NAMES = {
    "binance": "Binance",
    "bybit": "Bybit",
    "okx": "OKX",
    "kucoin": "KuCoin",
    "gateio": "GateIO",
    "mexc": "MEXC",
    "bitget": "Bitget",
    "htx": "HTX",
}


class CCXTExchange(BaseExchange):
    """Unified exchange adapter using CCXT library.

    All 8 exchanges share the same implementation — no custom adapters needed.
    Public data only, no API keys required.
    """

    def __init__(self, exchange_id: str):
        ccxt_id = CCXT_ID_MAP.get(exchange_id, exchange_id)
        exchange_class = getattr(ccxt_async, ccxt_id, None)
        if exchange_class is None:
            raise ValueError(f"CCXT does not support exchange: {ccxt_id}")

        self._exchange: ccxt_async.Exchange = exchange_class({
            "enableRateLimit": True,
            "timeout": 15000,
            "options": {"defaultType": "spot"},
        })
        self._exchange_id = exchange_id
        self.name = DISPLAY_NAMES.get(exchange_id, exchange_id.capitalize())
        self._markets_loaded = False
        self._lock = asyncio.Lock()
        self._latency_samples: list[float] = []

        # Futures instance (lazy, for funding rate / OI)
        self._futures: ccxt_async.Exchange | None = None
        self._futures_loaded = False
        self._futures_lock = asyncio.Lock()

    # ── Latency tracking ───────────────────────────

    @property
    def avg_latency_ms(self) -> float:
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)

    def _record_latency(self, ms: float):
        self._latency_samples.append(ms)
        if len(self._latency_samples) > 50:
            self._latency_samples = self._latency_samples[-50:]

    # ── Market loading ─────────────────────────────

    async def _ensure_markets(self):
        if self._markets_loaded:
            return
        async with self._lock:
            if self._markets_loaded:
                return
            try:
                await self._exchange.load_markets()
                self._markets_loaded = True
                logger.debug(f"CCXT markets loaded for {self.name}: {len(self._exchange.markets)} markets")
            except Exception as e:
                raise ExchangeError(f"Failed to load markets for {self.name}: {e}")

    async def _ensure_futures(self):
        if self._futures_loaded:
            return
        async with self._futures_lock:
            if self._futures_loaded:
                return
            try:
                ccxt_id = CCXT_ID_MAP.get(self._exchange_id, self._exchange_id)
                exchange_class = getattr(ccxt_async, ccxt_id)
                self._futures = exchange_class({
                    "enableRateLimit": True,
                    "timeout": 15000,
                    "options": {"defaultType": "swap"},
                })
                await self._futures.load_markets()
                self._futures_loaded = True
            except Exception as e:
                logger.debug(f"Futures markets not available for {self.name}: {e}")

    # ── Symbol conversion ──────────────────────────

    @staticmethod
    def _to_ccxt(symbol: str) -> str:
        """Convert 'BTCUSDT' → 'BTC/USDT'."""
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        return symbol

    @staticmethod
    def _from_ccxt(symbol: str) -> str:
        """Convert 'BTC/USDT' → 'BTCUSDT'."""
        return symbol.replace("/", "")

    # ── Timed call wrapper ─────────────────────────

    async def _timed_call(self, coro):
        start = time.monotonic()
        try:
            result = await coro
            elapsed = (time.monotonic() - start) * 1000
            self._record_latency(elapsed)
            return result
        except ccxt_async.BaseError as e:
            elapsed = (time.monotonic() - start) * 1000
            self._record_latency(elapsed)
            raise ExchangeError(f"{self.name}: {e}")

    # ── BaseExchange implementation ────────────────

    async def get_ticker(self, symbol: str) -> Ticker:
        await self._ensure_markets()
        ccxt_symbol = self._to_ccxt(symbol)
        data = await self._timed_call(self._exchange.fetch_ticker(ccxt_symbol))

        ts = None
        if data.get("timestamp"):
            ts = datetime.datetime.fromtimestamp(
                data["timestamp"] / 1000, tz=datetime.timezone.utc
            )

        return Ticker(
            symbol=self._from_ccxt(data.get("symbol", ccxt_symbol)),
            last_price=float(data.get("last") or 0),
            bid=float(data.get("bid") or 0),
            ask=float(data.get("ask") or 0),
            volume_24h=float(data.get("quoteVolume") or 0),
            price_change_24h=float(data.get("change") or 0),
            price_change_pct_24h=float(data.get("percentage") or 0),
            high_24h=float(data.get("high") or 0),
            low_24h=float(data.get("low") or 0),
            timestamp=ts,
        )

    async def get_klines(
        self, symbol: str, interval: str = "4h", limit: int = 200
    ) -> list[OHLCV]:
        await self._ensure_markets()
        ccxt_symbol = self._to_ccxt(symbol)
        data = await self._timed_call(
            self._exchange.fetch_ohlcv(ccxt_symbol, timeframe=interval, limit=limit)
        )

        results = []
        for candle in data:
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(
                    candle[0] / 1000, tz=datetime.timezone.utc
                ),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5] or 0),
            ))
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        await self._ensure_markets()
        ccxt_symbol = self._to_ccxt(symbol)
        data = await self._timed_call(
            self._exchange.fetch_order_book(ccxt_symbol, limit=limit)
        )

        ts = None
        if data.get("timestamp"):
            ts = datetime.datetime.fromtimestamp(
                data["timestamp"] / 1000, tz=datetime.timezone.utc
            )

        return OrderBook(
            symbol=self._from_ccxt(data.get("symbol", ccxt_symbol)),
            bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])],
            asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])],
            timestamp=ts,
        )

    async def get_all_tickers(self) -> list[Ticker]:
        await self._ensure_markets()
        raw = await self._timed_call(self._exchange.fetch_tickers())

        tickers = []
        for symbol, data in raw.items():
            if not symbol.endswith("/USDT"):
                continue
            # Only spot markets
            market = self._exchange.markets.get(symbol)
            if market and not market.get("spot", True):
                continue
            try:
                ts = None
                if data.get("timestamp"):
                    ts = datetime.datetime.fromtimestamp(
                        data["timestamp"] / 1000, tz=datetime.timezone.utc
                    )
                tickers.append(Ticker(
                    symbol=self._from_ccxt(symbol),
                    last_price=float(data.get("last") or 0),
                    bid=float(data.get("bid") or 0),
                    ask=float(data.get("ask") or 0),
                    volume_24h=float(data.get("quoteVolume") or 0),
                    price_change_24h=float(data.get("change") or 0),
                    price_change_pct_24h=float(data.get("percentage") or 0),
                    high_24h=float(data.get("high") or 0),
                    low_24h=float(data.get("low") or 0),
                    timestamp=ts,
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            await self._ensure_futures()
            if not self._futures:
                return None

            ccxt_symbol = self._to_ccxt(symbol)
            # Futures symbols often have ":USDT" suffix in CCXT
            futures_symbol = f"{ccxt_symbol}:USDT"
            if futures_symbol not in self._futures.markets:
                futures_symbol = ccxt_symbol
                if futures_symbol not in self._futures.markets:
                    return None

            data = await self._futures.fetch_funding_rate(futures_symbol)
            return FundingRate(
                symbol=self._from_ccxt(symbol),
                rate=float(data.get("fundingRate") or 0),
                next_funding_time=datetime.datetime.fromtimestamp(
                    data["nextFundingTimestamp"] / 1000, tz=datetime.timezone.utc
                ) if data.get("nextFundingTimestamp") else None,
            )
        except Exception as e:
            logger.debug(f"{self.name} funding rate unavailable for {symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            await self._ensure_futures()
            if not self._futures:
                return None

            ccxt_symbol = self._to_ccxt(symbol)
            futures_symbol = f"{ccxt_symbol}:USDT"
            if futures_symbol not in self._futures.markets:
                futures_symbol = ccxt_symbol
                if futures_symbol not in self._futures.markets:
                    return None

            data = await self._futures.fetch_open_interest(futures_symbol)
            return OpenInterest(
                symbol=self._from_ccxt(symbol),
                open_interest=float(data.get("openInterestAmount") or 0),
                open_interest_value=float(data.get("openInterestValue") or 0)
                if data.get("openInterestValue") else None,
            )
        except Exception as e:
            logger.debug(f"{self.name} OI unavailable for {symbol}: {e}")
            return None

    async def get_symbols(self) -> list[str]:
        await self._ensure_markets()
        symbols = []
        for symbol, market in self._exchange.markets.items():
            if (
                market.get("quote") == "USDT"
                and market.get("active", True)
                and market.get("spot", False)
            ):
                symbols.append(self._from_ccxt(symbol))
        return symbols

    async def close(self):
        try:
            await self._exchange.close()
        except Exception:
            pass
        if self._futures:
            try:
                await self._futures.close()
            except Exception:
                pass
