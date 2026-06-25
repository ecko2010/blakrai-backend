"""MEXC exchange adapter (public API v3)."""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError


class MEXCExchange(BaseExchange):
    name = "MEXC"

    def __init__(self, base_url: str = "https://api.mexc.com"):
        self._base_url = base_url
        self._futures_url = "https://contract.mexc.com"
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict | None = None) -> dict | list:
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_ticker(self, symbol: str) -> Ticker:
        data = await self._get(f"{self._base_url}/api/v3/ticker/24hr", {"symbol": symbol.upper()})
        last = float(data["lastPrice"])
        return Ticker(
            symbol=symbol.upper(),
            last_price=last,
            bid=float(data.get("bidPrice", last)),
            ask=float(data.get("askPrice", last)),
            volume_24h=float(data.get("quoteVolume", 0)),
            price_change_24h=float(data.get("priceChange", 0)),
            price_change_pct_24h=float(data.get("priceChangePercent", 0)),
            high_24h=float(data.get("highPrice", last)),
            low_24h=float(data.get("lowPrice", last)),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        # MEXC v3 klines use same format as Binance
        interval_map = {
            "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
            "12h": "12h", "1d": "1d", "1w": "1w",
        }
        mexc_interval = interval_map.get(interval, "4h")
        data = await self._get(f"{self._base_url}/api/v3/klines", {
            "symbol": symbol.upper(), "interval": mexc_interval, "limit": str(limit),
        })
        results = []
        for k in data if isinstance(data, list) else []:
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
        data = await self._get(f"{self._base_url}/api/v3/depth", {
            "symbol": symbol.upper(), "limit": str(limit),
        })
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])[:limit]],
            asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])[:limit]],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get(f"{self._base_url}/api/v3/ticker/24hr")
        tickers = []
        for d in data if isinstance(data, list) else []:
            sym = d.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            try:
                last = float(d["lastPrice"])
                tickers.append(Ticker(
                    symbol=sym,
                    last_price=last,
                    bid=float(d.get("bidPrice", last)),
                    ask=float(d.get("askPrice", last)),
                    volume_24h=float(d.get("quoteVolume", 0)),
                    price_change_24h=float(d.get("priceChange", 0)),
                    price_change_pct_24h=float(d.get("priceChangePercent", 0)),
                    high_24h=float(d.get("highPrice", last)),
                    low_24h=float(d.get("lowPrice", last)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            # MEXC contract API: symbol format BTC_USDT
            contract_sym = symbol.upper().replace("USDT", "_USDT")
            data = await self._get(f"{self._futures_url}/api/v1/contract/funding_rate/{contract_sym}")
            if isinstance(data, dict) and data.get("success") and data.get("data"):
                return FundingRate(
                    symbol=symbol,
                    rate=float(data["data"]["fundingRate"]),
                    next_funding_time=datetime.datetime.fromtimestamp(
                        int(data["data"]["nextSettleTime"]) / 1000, tz=datetime.timezone.utc
                    ) if data["data"].get("nextSettleTime") else None,
                )
        except Exception:
            pass
        return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            contract_sym = symbol.upper().replace("USDT", "_USDT")
            data = await self._get(f"{self._futures_url}/api/v1/contract/detail", {"symbol": contract_sym})
            if isinstance(data, dict) and data.get("success") and data.get("data"):
                return OpenInterest(
                    symbol=symbol,
                    open_interest=float(data["data"].get("openInterest", 0)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
        except Exception:
            pass
        return None

    async def get_symbols(self) -> list[str]:
        data = await self._get(f"{self._base_url}/api/v3/exchangeInfo")
        symbols = []
        if isinstance(data, dict):
            for s in data.get("symbols", []):
                if s.get("status") == "1" and s["symbol"].endswith("USDT"):
                    symbols.append(s["symbol"])
        return symbols

    async def close(self):
        await self._client.aclose()
