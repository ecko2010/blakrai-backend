"""
Bybit exchange adapter (public API v5).
"""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest
from app.config import settings


class BybitExchange(BaseExchange):
    name = "Bybit"

    def __init__(self):
        self._base_url = settings.BYBIT_BASE_URL
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        resp = await self._client.get(f"{self._base_url}{endpoint}", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("retCode") != 0:
            raise Exception(f"Bybit API error: {data.get('retMsg')}")
        return data.get("result", {})

    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._get("/v5/market/tickers", {
            "category": "spot",
            "symbol": symbol.upper(),
        })
        item = data["list"][0]
        return Ticker(
            symbol=item["symbol"],
            last_price=float(item["lastPrice"]),
            bid=float(item["bid1Price"]),
            ask=float(item["ask1Price"]),
            volume_24h=float(item["turnover24h"]),
            price_change_24h=float(item["lastPrice"]) - float(item["prevPrice24h"]),
            price_change_pct_24h=float(item["price24hPcnt"]) * 100,
            high_24h=float(item["highPrice24h"]),
            low_24h=float(item["lowPrice24h"]),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "240", limit: int = 200) -> list[OHLCV]:
        interval_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
            "1d": "D", "1w": "W", "1M": "M",
        }
        bybit_interval = interval_map.get(interval, interval)
        data = await self._get("/v5/market/kline", {
            "category": "spot",
            "symbol": symbol.upper(),
            "interval": bybit_interval,
            "limit": limit,
        })
        results = []
        for k in reversed(data.get("list", [])):
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(int(k[0]) / 1000, tz=datetime.timezone.utc),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
            ))
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        data = await self._get("/v5/market/orderbook", {
            "category": "spot",
            "symbol": symbol.upper(),
            "limit": limit,
        })
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data.get("b", [])],
            asks=[(float(a[0]), float(a[1])) for a in data.get("a", [])],
            timestamp=datetime.datetime.fromtimestamp(
                int(data.get("ts", 0)) / 1000, tz=datetime.timezone.utc
            ),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get("/v5/market/tickers", {"category": "spot"})
        tickers = []
        for d in data.get("list", []):
            if not d["symbol"].endswith("USDT"):
                continue
            try:
                tickers.append(Ticker(
                    symbol=d["symbol"],
                    last_price=float(d["lastPrice"]),
                    bid=float(d["bid1Price"]),
                    ask=float(d["ask1Price"]),
                    volume_24h=float(d["turnover24h"]),
                    price_change_24h=float(d["lastPrice"]) - float(d["prevPrice24h"]),
                    price_change_pct_24h=float(d["price24hPcnt"]) * 100,
                    high_24h=float(d["highPrice24h"]),
                    low_24h=float(d["lowPrice24h"]),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            data = await self._get("/v5/market/tickers", {
                "category": "linear",
                "symbol": symbol.upper(),
            })
            item = data["list"][0]
            return FundingRate(
                symbol=item["symbol"],
                rate=float(item.get("fundingRate", 0)),
                next_funding_time=datetime.datetime.fromtimestamp(
                    int(item["nextFundingTime"]) / 1000, tz=datetime.timezone.utc
                ) if item.get("nextFundingTime") else None,
            )
        except Exception as e:
            logger.debug(f"Bybit funding rate unavailable for {symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            data = await self._get("/v5/market/open-interest", {
                "category": "linear",
                "symbol": symbol.upper(),
                "intervalTime": "5min",
                "limit": 1,
            })
            item = data["list"][0]
            return OpenInterest(
                symbol=symbol.upper(),
                open_interest=float(item["openInterest"]),
            )
        except Exception as e:
            logger.debug(f"Bybit OI unavailable for {symbol}: {e}")
            return None

    async def get_symbols(self) -> list[str]:
        data = await self._get("/v5/market/instruments-info", {"category": "spot"})
        return [
            s["symbol"]
            for s in data.get("list", [])
            if s.get("status") == "Trading" and s["symbol"].endswith("USDT")
        ]

    async def close(self):
        await self._client.aclose()
