"""
Binance exchange adapter (public API, no auth needed).
Supports both spot and futures endpoints.
"""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest
from app.config import settings


class BinanceExchange(BaseExchange):
    name = "Binance"

    def __init__(self):
        self._spot_url = settings.BINANCE_BASE_URL
        self._futures_url = "https://fapi.binance.com"
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict | None = None) -> dict | list:
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._get(
            f"{self._spot_url}/api/v3/ticker/24hr",
            {"symbol": symbol.upper()},
        )
        return Ticker(
            symbol=data["symbol"],
            last_price=float(data["lastPrice"]),
            bid=float(data["bidPrice"]),
            ask=float(data["askPrice"]),
            volume_24h=float(data["quoteVolume"]),
            price_change_24h=float(data["priceChange"]),
            price_change_pct_24h=float(data["priceChangePercent"]),
            high_24h=float(data["highPrice"]),
            low_24h=float(data["lowPrice"]),
            timestamp=datetime.datetime.fromtimestamp(
                data["closeTime"] / 1000, tz=datetime.timezone.utc
            ),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        data = await self._get(
            f"{self._spot_url}/api/v3/klines",
            {"symbol": symbol.upper(), "interval": interval, "limit": limit},
        )
        results = []
        for k in data:
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(k[0] / 1000, tz=datetime.timezone.utc),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
            ))
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        data = await self._get(
            f"{self._spot_url}/api/v3/depth",
            {"symbol": symbol.upper(), "limit": limit},
        )
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data["bids"]],
            asks=[(float(a[0]), float(a[1])) for a in data["asks"]],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get(f"{self._spot_url}/api/v3/ticker/24hr")
        tickers = []
        for d in data:
            if not d["symbol"].endswith("USDT"):
                continue
            try:
                tickers.append(Ticker(
                    symbol=d["symbol"],
                    last_price=float(d["lastPrice"]),
                    bid=float(d["bidPrice"]),
                    ask=float(d["askPrice"]),
                    volume_24h=float(d["quoteVolume"]),
                    price_change_24h=float(d["priceChange"]),
                    price_change_pct_24h=float(d["priceChangePercent"]),
                    high_24h=float(d["highPrice"]),
                    low_24h=float(d["lowPrice"]),
                    timestamp=datetime.datetime.fromtimestamp(
                        d["closeTime"] / 1000, tz=datetime.timezone.utc
                    ),
                ))
            except (ValueError, KeyError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            data = await self._get(
                f"{self._futures_url}/fapi/v1/fundingRate",
                {"symbol": symbol.upper(), "limit": 1},
            )
            if not data:
                return None
            return FundingRate(
                symbol=symbol.upper(),
                rate=float(data[0]["fundingRate"]),
                next_funding_time=datetime.datetime.fromtimestamp(
                    data[0].get("fundingTime", 0) / 1000, tz=datetime.timezone.utc
                ) if data[0].get("fundingTime") else None,
            )
        except Exception as e:
            logger.debug(f"Funding rate not available for {symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            data = await self._get(
                f"{self._futures_url}/fapi/v1/openInterest",
                {"symbol": symbol.upper()},
            )
            return OpenInterest(
                symbol=data["symbol"],
                open_interest=float(data["openInterest"]),
            )
        except Exception as e:
            logger.debug(f"Open interest not available for {symbol}: {e}")
            return None

    async def get_symbols(self) -> list[str]:
        data = await self._get(f"{self._spot_url}/api/v3/exchangeInfo")
        return [
            s["symbol"]
            for s in data["symbols"]
            if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
        ]

    async def close(self):
        await self._client.aclose()
