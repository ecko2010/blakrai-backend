"""Bitget exchange adapter (public API v2)."""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError


class BitgetExchange(BaseExchange):
    name = "Bitget"

    def __init__(self, base_url: str = "https://api.bitget.com"):
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        resp = await self._client.get(f"{self._base_url}{endpoint}", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "00000":
            raise ExchangeError(f"[Bitget] {data.get('msg', 'Unknown error')}")
        return data.get("data", {})

    def _to_bitget_symbol(self, symbol: str) -> str:
        """BTCUSDT → BTCUSDT (spot) / BTCUSDT (mix: USDT futures)"""
        return symbol.upper()

    async def get_ticker(self, symbol: str) -> Ticker:
        sym = self._to_bitget_symbol(symbol)
        data = await self._get("/api/v2/spot/market/tickers", {"symbol": sym})
        if isinstance(data, list) and data:
            d = data[0]
        elif isinstance(data, dict):
            d = data
        else:
            raise ExchangeError(f"[Bitget] No ticker for {symbol}")
        last = float(d.get("lastPr", d.get("close", 0)))
        open_price = float(d.get("open", last))
        return Ticker(
            symbol=symbol.upper(),
            last_price=last,
            bid=float(d.get("bidPr", last)),
            ask=float(d.get("askPr", last)),
            volume_24h=float(d.get("quoteVolume", d.get("usdtVolume", 0))),
            price_change_24h=last - open_price,
            price_change_pct_24h=float(d.get("change", 0)) * 100 if d.get("change") else 0,
            high_24h=float(d.get("high24h", d.get("high", last))),
            low_24h=float(d.get("low24h", d.get("low", last))),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        interval_map = {
            "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "1h", "4h": "4h", "6h": "6h", "12h": "12h", "1d": "1day", "1w": "1week",
        }
        bg_interval = interval_map.get(interval, "4h")
        sym = self._to_bitget_symbol(symbol)

        data = await self._get("/api/v2/spot/market/candles", {
            "symbol": sym, "granularity": bg_interval, "limit": str(limit),
        })

        results = []
        candle_list = data if isinstance(data, list) else []
        for k in reversed(candle_list):
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
        sym = self._to_bitget_symbol(symbol)
        data = await self._get("/api/v2/spot/market/orderbook", {
            "symbol": sym, "limit": str(min(limit, 150)),
        })
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])[:limit]],
            asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])[:limit]],
            timestamp=datetime.datetime.fromtimestamp(
                int(data["ts"]) / 1000, tz=datetime.timezone.utc
            ) if data.get("ts") else datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get("/api/v2/spot/market/tickers")
        tickers = []
        for d in data if isinstance(data, list) else []:
            sym = d.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            try:
                last = float(d.get("lastPr", d.get("close", 0)))
                if last == 0:
                    continue
                open_price = float(d.get("open", last))
                tickers.append(Ticker(
                    symbol=sym,
                    last_price=last,
                    bid=float(d.get("bidPr", last)),
                    ask=float(d.get("askPr", last)),
                    volume_24h=float(d.get("quoteVolume", d.get("usdtVolume", 0))),
                    price_change_24h=last - open_price,
                    price_change_pct_24h=float(d.get("change", 0)) * 100 if d.get("change") else 0,
                    high_24h=float(d.get("high24h", d.get("high", last))),
                    low_24h=float(d.get("low24h", d.get("low", last))),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            # Bitget mix (USDT-M futures)
            sym = self._to_bitget_symbol(symbol)
            data = await self._get("/api/v2/mix/market/current-fund-rate", {
                "symbol": sym, "productType": "USDT-FUTURES",
            })
            if isinstance(data, list) and data:
                d = data[0]
            elif isinstance(data, dict):
                d = data
            else:
                return None
            return FundingRate(
                symbol=symbol,
                rate=float(d.get("fundingRate", 0)),
                next_funding_time=None,
            )
        except Exception:
            return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            sym = self._to_bitget_symbol(symbol)
            data = await self._get("/api/v2/mix/market/open-interest", {
                "symbol": sym, "productType": "USDT-FUTURES",
            })
            if isinstance(data, dict) and data.get("openInterest"):
                return OpenInterest(
                    symbol=symbol,
                    open_interest=float(data["openInterest"]),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
        except Exception:
            pass
        return None

    async def get_symbols(self) -> list[str]:
        data = await self._get("/api/v2/spot/public/symbols")
        return [
            s["symbol"]
            for s in (data if isinstance(data, list) else [])
            if s.get("status") == "online" and s["symbol"].endswith("USDT")
        ]

    async def close(self):
        await self._client.aclose()
