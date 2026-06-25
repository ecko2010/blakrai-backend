"""Exchange manager — unified access to all exchanges with cross-exchange aggregation."""

import asyncio
from typing import Any
from loguru import logger

from app.exchanges.base import BaseExchange, Ticker, Candle, OrderBook, ExchangeError
from app.exchanges.ccxt_client import CCXTExchange
from app.exchanges.scoring import exchange_scorer


# All supported exchanges — CCXT handles API differences internally
SUPPORTED_EXCHANGES = [
    "binance", "bybit", "okx", "kucoin",
    "gateio", "mexc", "bitget", "htx",
]


class ExchangeManager:
    """Manages all exchange connections and provides cross-exchange data."""

    def __init__(self):
        self.exchanges: dict[str, BaseExchange] = {}
        self._init_exchanges()

    def _init_exchanges(self):
        for exchange_id in SUPPORTED_EXCHANGES:
            try:
                self.exchanges[exchange_id] = CCXTExchange(exchange_id)
            except Exception as e:
                logger.error(f"Failed to init {exchange_id}: {e}")

    def get_exchange(self, name: str) -> BaseExchange:
        name = name.lower()
        if name not in self.exchanges:
            raise ValueError(f"Exchange '{name}' not supported. Available: {list(self.exchanges.keys())}")
        return self.exchanges[name]

    async def get_ticker_all_exchanges(self, symbol: str) -> dict[str, Ticker | None]:
        """Get ticker for a symbol from all exchanges simultaneously."""
        results = {}

        async def _fetch(name: str, exchange: BaseExchange):
            try:
                results[name] = await exchange.get_ticker(symbol)
            except Exception as e:
                logger.debug(f"Ticker for {symbol} not available on {name}: {e}")
                results[name] = None

        await asyncio.gather(*[_fetch(n, e) for n, e in self.exchanges.items()])
        return results

    async def get_candles_all_exchanges(
        self, symbol: str, interval: str, limit: int = 200
    ) -> dict[str, list[Candle]]:
        """Get candles from all exchanges simultaneously."""
        results = {}

        async def _fetch(name: str, exchange: BaseExchange):
            try:
                results[name] = await exchange.get_candles(symbol, interval, limit)
            except Exception as e:
                logger.debug(f"Candles for {symbol} not available on {name}: {e}")
                results[name] = []

        await asyncio.gather(*[_fetch(n, e) for n, e in self.exchanges.items()])
        return results

    async def get_best_price(self, symbol: str) -> dict[str, Any]:
        """Get the best bid/ask across all exchanges."""
        tickers = await self.get_ticker_all_exchanges(symbol)
        best_bid = None
        best_ask = None
        best_bid_exchange = None
        best_ask_exchange = None

        for name, ticker in tickers.items():
            if ticker is None:
                continue
            if best_bid is None or ticker.bid > best_bid:
                best_bid = ticker.bid
                best_bid_exchange = name
            if best_ask is None or ticker.ask < best_ask:
                best_ask = ticker.ask
                best_ask_exchange = name

        return {
            "best_bid": best_bid,
            "best_bid_exchange": best_bid_exchange,
            "best_ask": best_ask,
            "best_ask_exchange": best_ask_exchange,
            "spread": (best_ask - best_bid) if best_ask and best_bid else None,
            "tickers": {k: v for k, v in tickers.items() if v is not None},
        }

    async def get_cross_exchange_volume(self, symbol: str) -> dict[str, float]:
        """Get 24h volume across all exchanges."""
        tickers = await self.get_ticker_all_exchanges(symbol)
        return {
            name: ticker.volume_24h
            for name, ticker in tickers.items()
            if ticker is not None
        }

    async def detect_price_divergence(self, symbol: str, threshold_pct: float = 0.5) -> dict | None:
        """Detect significant price differences between exchanges (arbitrage opportunity / anomaly)."""
        tickers = await self.get_ticker_all_exchanges(symbol)
        active = {k: v for k, v in tickers.items() if v is not None}

        if len(active) < 2:
            return None

        prices = {name: t.last_price for name, t in active.items()}
        max_name = max(prices, key=prices.get)
        min_name = min(prices, key=prices.get)

        max_price = prices[max_name]
        min_price = prices[min_name]

        if min_price == 0:
            return None

        divergence_pct = ((max_price - min_price) / min_price) * 100

        if divergence_pct >= threshold_pct:
            return {
                "symbol": symbol,
                "divergence_pct": round(divergence_pct, 4),
                "high_exchange": max_name,
                "high_price": max_price,
                "low_exchange": min_name,
                "low_price": min_price,
            }
        return None

    async def get_aggregated_orderbook(self, symbol: str, limit: int = 10) -> dict:
        """Get combined orderbook depth across all exchanges."""
        results = {}

        async def _fetch(name: str, exchange: BaseExchange):
            try:
                results[name] = await exchange.get_orderbook(symbol, limit)
            except Exception:
                results[name] = None

        await asyncio.gather(*[_fetch(n, e) for n, e in self.exchanges.items()])

        total_bid_volume = 0.0
        total_ask_volume = 0.0
        for ob in results.values():
            if ob:
                for lvl in ob.bids:
                    total_bid_volume += lvl.quantity if hasattr(lvl, "quantity") else lvl[1]
                for lvl in ob.asks:
                    total_ask_volume += lvl.quantity if hasattr(lvl, "quantity") else lvl[1]

        buy_pressure = total_bid_volume / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0.5

        return {
            "orderbooks": {k: v for k, v in results.items() if v is not None},
            "total_bid_volume": total_bid_volume,
            "total_ask_volume": total_ask_volume,
            "buy_pressure": round(buy_pressure, 4),
        }

    async def close_all(self):
        for exchange in self.exchanges.values():
            await exchange.close()


# Singleton
exchange_manager = ExchangeManager()
