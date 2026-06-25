"""KuCoin exchange adapter (public API v1/v3)."""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError


class KuCoinExchange(BaseExchange):
    name = "KuCoin"

    def __init__(self, base_url: str = "https://api.kucoin.com"):
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        resp = await self._client.get(f"{self._base_url}{endpoint}", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "200000":
            raise ExchangeError(f"[KuCoin] {data.get('msg', 'Unknown error')}")
        return data.get("data", {})

    def _to_kucoin_symbol(self, symbol: str) -> str:
        """BTCUSDT → BTC-USDT"""
        return symbol.replace("USDT", "-USDT")

    async def get_ticker(self, symbol: str) -> Ticker:
        kc_symbol = self._to_kucoin_symbol(symbol)
        data = await self._get("/api/v1/market/stats", {"symbol": kc_symbol})
        last = float(data["last"])
        open_price = float(data.get("open", last))
        return Ticker(
            symbol=symbol.upper(),
            last_price=last,
            bid=float(data.get("buy", last)),
            ask=float(data.get("sell", last)),
            volume_24h=float(data.get("volValue", 0)),
            price_change_24h=last - open_price,
            price_change_pct_24h=float(data.get("changeRate", 0)) * 100,
            high_24h=float(data.get("high", last)),
            low_24h=float(data.get("low", last)),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        interval_map = {
            "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour", "8h": "8hour",
            "12h": "12hour", "1d": "1day", "1w": "1week",
        }
        kc_interval = interval_map.get(interval, "4hour")
        kc_symbol = self._to_kucoin_symbol(symbol)

        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        # KuCoin uses seconds, limit via startAt/endAt
        interval_seconds = {"1min": 60, "3min": 180, "5min": 300, "15min": 900, "30min": 1800,
                            "1hour": 3600, "2hour": 7200, "4hour": 14400, "6hour": 21600,
                            "8hour": 28800, "12hour": 43200, "1day": 86400, "1week": 604800}
        secs = interval_seconds.get(kc_interval, 14400)
        start_at = now - (limit * secs)

        data = await self._get("/api/v1/market/candles", {
            "symbol": kc_symbol, "type": kc_interval,
            "startAt": str(start_at), "endAt": str(now),
        })
        results = []
        for k in reversed(data if isinstance(data, list) else []):
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(int(k[0]), tz=datetime.timezone.utc),
                open=float(k[1]),
                high=float(k[3]),
                low=float(k[4]),
                close=float(k[2]),
                volume=float(k[5]),
            ))
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        kc_symbol = self._to_kucoin_symbol(symbol)
        depth = "20" if limit <= 20 else "100"
        data = await self._get(f"/api/v1/market/orderbook/level2_{depth}", {"symbol": kc_symbol})
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])[:limit]],
            asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])[:limit]],
            timestamp=datetime.datetime.fromtimestamp(
                int(data.get("time", 0)) / 1000, tz=datetime.timezone.utc
            ) if data.get("time") else datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get("/api/v1/market/allTickers")
        tickers = []
        for d in data.get("ticker", []):
            sym = d.get("symbol", "")
            if not sym.endswith("-USDT"):
                continue
            try:
                last = float(d["last"])
                open_price = float(d.get("open", last)) if d.get("open") else last
                tickers.append(Ticker(
                    symbol=sym.replace("-", ""),
                    last_price=last,
                    bid=float(d.get("buy", last)),
                    ask=float(d.get("sell", last)),
                    volume_24h=float(d.get("volValue", 0)),
                    price_change_24h=last - open_price,
                    price_change_pct_24h=float(d.get("changeRate", 0)) * 100,
                    high_24h=float(d.get("high", last)),
                    low_24h=float(d.get("low", last)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            # KuCoin Futures: separate API domain
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api-futures.kucoin.com/api/v1/funding-rate/{self._to_kucoin_symbol(symbol)}/current"
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "200000":
                    return None
                return FundingRate(
                    symbol=symbol,
                    rate=float(data["data"]["value"]),
                    next_funding_time=datetime.datetime.fromtimestamp(
                        int(data["data"]["timePoint"]) / 1000, tz=datetime.timezone.utc
                    ) if data["data"].get("timePoint") else None,
                )
        except Exception:
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        return None  # KuCoin Futures OI requires auth

    async def get_symbols(self) -> list[str]:
        data = await self._get("/api/v2/symbols")
        return [
            s["symbol"].replace("-", "")
            for s in (data if isinstance(data, list) else [])
            if s.get("enableTrading") and s["symbol"].endswith("-USDT")
        ]

    async def close(self):
        await self._client.aclose()
