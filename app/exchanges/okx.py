"""OKX exchange integration (public API v5)."""

import httpx
from datetime import datetime, timezone
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, Candle, Ticker, OrderBook, OrderBookLevel, OHLCV, ExchangeError, FundingRate, OpenInterest


INTERVAL_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
    "1d": "1D", "1w": "1W", "1M": "1M",
}


class OKXExchange(BaseExchange):
    name = "OKX"

    def __init__(self, base_url: str = "https://www.okx.com"):
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        resp = await self._client.get(f"{self._base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _parse_response(self, data: dict) -> list:
        if data.get("code") != "0":
            raise ExchangeError(f"[OKX] {data.get('msg', 'Unknown error')}")
        return data.get("data", [])

    async def get_ticker(self, symbol: str) -> Ticker:
        inst_id = symbol.replace("USDT", "-USDT")
        data = self._parse_response(await self._get("/api/v5/market/ticker", {"instId": inst_id}))
        item = data[0]
        last = float(item["last"])
        open24h = float(item["open24h"]) if item.get("open24h") else last
        return Ticker(
            symbol=symbol,
            last_price=last,
            bid=float(item["bidPx"]),
            ask=float(item["askPx"]),
            volume_24h=float(item["volCcy24h"]),
            price_change_24h=last - open24h,
            price_change_pct_24h=((last - open24h) / open24h * 100) if open24h else 0,
            high_24h=float(item["high24h"]),
            low_24h=float(item["low24h"]),
        )

    async def get_candles(self, symbol: str, interval: str, limit: int = 200) -> list[Candle]:
        inst_id = symbol.replace("USDT", "-USDT")
        okx_interval = INTERVAL_MAP.get(interval, interval)
        data = self._parse_response(await self._get("/api/v5/market/candles", {
            "instId": inst_id,
            "bar": okx_interval,
            "limit": str(min(limit, 300)),
        }))
        candles = []
        for item in data:
            candles.append(Candle(
                timestamp=datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc),
                o=float(item[1]),
                h=float(item[2]),
                l=float(item[3]),
                c=float(item[4]),
                v=float(item[5]),
            ))
        candles.reverse()
        return candles

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        inst_id = symbol.replace("USDT", "-USDT")
        data = self._parse_response(await self._get("/api/v5/market/books", {
            "instId": inst_id, "sz": str(limit)
        }))
        item = data[0] if data else {"bids": [], "asks": []}
        bids = [OrderBookLevel(float(p), float(q)) for p, q, *_ in item.get("bids", [])]
        asks = [OrderBookLevel(float(p), float(q)) for p, q, *_ in item.get("asks", [])]
        return OrderBook(bids=bids, asks=asks)

    async def get_all_tickers(self) -> list[Ticker]:
        data = self._parse_response(await self._get("/api/v5/market/tickers", {"instType": "SPOT"}))
        tickers = []
        for item in data:
            if not item["instId"].endswith("-USDT"):
                continue
            last = float(item["last"])
            open24h = float(item["open24h"]) if item.get("open24h") else last
            tickers.append(Ticker(
                symbol=item["instId"].replace("-", ""),
                last_price=last,
                bid=float(item["bidPx"]) if item.get("bidPx") else last,
                ask=float(item["askPx"]) if item.get("askPx") else last,
                volume_24h=float(item["volCcy24h"]),
                price_change_24h=last - open24h,
                price_change_pct_24h=((last - open24h) / open24h * 100) if open24h else 0,
                high_24h=float(item["high24h"]),
                low_24h=float(item["low24h"]),
            ))
        return tickers

    async def get_trading_pairs(self) -> list[str]:
        data = self._parse_response(await self._get("/api/v5/public/instruments", {"instType": "SPOT"}))
        return [
            s["instId"].replace("-", "")
            for s in data
            if s.get("state") == "live" and s["instId"].endswith("-USDT")
        ]

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        """get_klines via get_candles conversion."""
        candles = await self.get_candles(symbol, interval, limit)
        return [
            OHLCV(timestamp=c.timestamp, open=c.o, high=c.h, low=c.l, close=c.c, volume=c.v)
            for c in candles
        ]

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            inst_id = symbol.replace("USDT", "-USDT-SWAP")
            data = self._parse_response(await self._get("/api/v5/public/funding-rate", {"instId": inst_id}))
            if not data:
                return None
            return FundingRate(
                symbol=symbol,
                rate=float(data[0]["fundingRate"]),
                next_funding_time=datetime.fromtimestamp(
                    int(data[0]["fundingTime"]) / 1000, tz=timezone.utc
                ) if data[0].get("fundingTime") else None,
            )
        except Exception:
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            inst_id = symbol.replace("USDT", "-USDT-SWAP")
            data = self._parse_response(await self._get("/api/v5/public/open-interest", {"instId": inst_id}))
            if not data:
                return None
            return OpenInterest(
                symbol=symbol,
                open_interest=float(data[0]["oi"]),
                open_interest_value=float(data[0].get("oiCcy", 0)),
            )
        except Exception:
            return None

    async def get_symbols(self) -> list[str]:
        return await self.get_trading_pairs()

    async def close(self):
        await self._client.aclose()
