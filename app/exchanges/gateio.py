"""Gate.io exchange adapter (public API v4)."""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError


class GateIOExchange(BaseExchange):
    name = "GateIO"

    def __init__(self, base_url: str = "https://api.gateio.ws"):
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, endpoint: str, params: dict | None = None) -> list | dict:
        resp = await self._client.get(f"{self._base_url}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _to_gate_symbol(self, symbol: str) -> str:
        """BTCUSDT → BTC_USDT"""
        return symbol.replace("USDT", "_USDT")

    async def get_ticker(self, symbol: str) -> Ticker:
        gate_sym = self._to_gate_symbol(symbol)
        data_list = await self._get("/api/v4/spot/tickers", {"currency_pair": gate_sym})
        if not data_list:
            raise ExchangeError(f"[GateIO] No ticker data for {symbol}")
        d = data_list[0] if isinstance(data_list, list) else data_list
        last = float(d["last"])
        change_pct = float(d.get("change_percentage", 0))
        return Ticker(
            symbol=symbol.upper(),
            last_price=last,
            bid=float(d.get("highest_bid", last)),
            ask=float(d.get("lowest_ask", last)),
            volume_24h=float(d.get("quote_volume", 0)),
            price_change_24h=last * change_pct / 100,
            price_change_pct_24h=change_pct,
            high_24h=float(d.get("high_24h", last)),
            low_24h=float(d.get("low_24h", last)),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h",
            "1d": "1d", "1w": "7d",
        }
        gate_interval = interval_map.get(interval, "4h")
        gate_sym = self._to_gate_symbol(symbol)
        data = await self._get("/api/v4/spot/candlesticks", {
            "currency_pair": gate_sym, "interval": gate_interval, "limit": str(limit),
        })
        results = []
        for k in data if isinstance(data, list) else []:
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(int(k[0]), tz=datetime.timezone.utc),
                open=float(k[5]),
                high=float(k[3]),
                low=float(k[4]),
                close=float(k[2]),
                volume=float(k[1]),
            ))
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        gate_sym = self._to_gate_symbol(symbol)
        data = await self._get("/api/v4/spot/order_book", {
            "currency_pair": gate_sym, "limit": str(limit),
        })
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])[:limit]],
            asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])[:limit]],
            timestamp=datetime.datetime.fromtimestamp(
                int(data.get("current", 0)) / 1000, tz=datetime.timezone.utc
            ) if data.get("current") else datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get("/api/v4/spot/tickers")
        tickers = []
        for d in data if isinstance(data, list) else []:
            pair = d.get("currency_pair", "")
            if not pair.endswith("_USDT"):
                continue
            try:
                last = float(d["last"])
                change_pct = float(d.get("change_percentage", 0))
                tickers.append(Ticker(
                    symbol=pair.replace("_", ""),
                    last_price=last,
                    bid=float(d.get("highest_bid", last)),
                    ask=float(d.get("lowest_ask", last)),
                    volume_24h=float(d.get("quote_volume", 0)),
                    price_change_24h=last * change_pct / 100,
                    price_change_pct_24h=change_pct,
                    high_24h=float(d.get("high_24h", last)),
                    low_24h=float(d.get("low_24h", last)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            gate_sym = self._to_gate_symbol(symbol)
            data = await self._get(f"/api/v4/futures/usdt/contracts/{gate_sym}")
            if isinstance(data, dict) and data.get("funding_rate"):
                return FundingRate(
                    symbol=symbol,
                    rate=float(data["funding_rate"]),
                    next_funding_time=datetime.datetime.fromtimestamp(
                        int(data["funding_next_apply"]), tz=datetime.timezone.utc
                    ) if data.get("funding_next_apply") else None,
                )
        except Exception:
            pass
        return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            gate_sym = self._to_gate_symbol(symbol)
            data = await self._get(f"/api/v4/futures/usdt/contracts/{gate_sym}")
            if isinstance(data, dict) and data.get("position_size"):
                return OpenInterest(
                    symbol=symbol,
                    open_interest=float(data["position_size"]),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
        except Exception:
            pass
        return None

    async def get_symbols(self) -> list[str]:
        data = await self._get("/api/v4/spot/currency_pairs")
        return [
            d["id"].replace("_", "")
            for d in (data if isinstance(data, list) else [])
            if d.get("trade_status") == "tradable" and d["id"].endswith("_USDT")
        ]

    async def close(self):
        await self._client.aclose()
