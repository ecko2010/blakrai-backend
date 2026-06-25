"""HTX (ex-Huobi) exchange adapter (public API v1/v2)."""

import datetime
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.exchanges.base import BaseExchange, OHLCV, Ticker, OrderBook, FundingRate, OpenInterest, ExchangeError


class HTXExchange(BaseExchange):
    name = "HTX"

    def __init__(self, base_url: str = "https://api.huobi.pro"):
        self._base_url = base_url
        self._futures_url = "https://api.hbdm.com"
        self._client = httpx.AsyncClient(timeout=15.0, http2=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, url: str, params: dict | None = None) -> dict:
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "error":
            raise ExchangeError(f"[HTX] {data.get('err-msg', 'Unknown error')}")
        return data

    def _to_htx_symbol(self, symbol: str) -> str:
        """BTCUSDT → btcusdt (HTX uses lowercase)."""
        return symbol.lower()

    async def get_ticker(self, symbol: str) -> Ticker:
        htx_sym = self._to_htx_symbol(symbol)
        data = await self._get(f"{self._base_url}/market/detail/merged", {"symbol": htx_sym})
        tick = data.get("tick", {})
        last = float(tick.get("close", 0))
        open_price = float(tick.get("open", last))
        return Ticker(
            symbol=symbol.upper(),
            last_price=last,
            bid=float(tick["bid"][0]) if tick.get("bid") else last,
            ask=float(tick["ask"][0]) if tick.get("ask") else last,
            volume_24h=float(tick.get("vol", 0)),
            price_change_24h=last - open_price,
            price_change_pct_24h=((last - open_price) / open_price * 100) if open_price else 0,
            high_24h=float(tick.get("high", last)),
            low_24h=float(tick.get("low", last)),
            timestamp=datetime.datetime.fromtimestamp(
                int(data.get("ts", 0)) / 1000, tz=datetime.timezone.utc
            ) if data.get("ts") else datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_klines(self, symbol: str, interval: str = "4h", limit: int = 200) -> list[OHLCV]:
        interval_map = {
            "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
            "1h": "60min", "4h": "4hour", "1d": "1day", "1w": "1week",
        }
        htx_interval = interval_map.get(interval, "4hour")
        htx_sym = self._to_htx_symbol(symbol)

        data = await self._get(f"{self._base_url}/market/history/kline", {
            "symbol": htx_sym, "period": htx_interval, "size": str(min(limit, 2000)),
        })
        results = []
        for k in data.get("data", []):
            results.append(OHLCV(
                timestamp=datetime.datetime.fromtimestamp(int(k["id"]), tz=datetime.timezone.utc),
                open=float(k["open"]),
                high=float(k["high"]),
                low=float(k["low"]),
                close=float(k["close"]),
                volume=float(k.get("vol", k.get("amount", 0))),
            ))
        # HTX returns newest first → reverse to chronological order
        results.reverse()
        return results

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        htx_sym = self._to_htx_symbol(symbol)
        depth_type = "step0"
        data = await self._get(f"{self._base_url}/market/depth", {
            "symbol": htx_sym, "type": depth_type, "depth": str(min(limit, 150)),
        })
        tick = data.get("tick", {})
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(float(b[0]), float(b[1])) for b in tick.get("bids", [])[:limit]],
            asks=[(float(a[0]), float(a[1])) for a in tick.get("asks", [])[:limit]],
            timestamp=datetime.datetime.fromtimestamp(
                int(tick.get("ts", data.get("ts", 0))) / 1000, tz=datetime.timezone.utc
            ) if tick.get("ts") or data.get("ts") else datetime.datetime.now(datetime.timezone.utc),
        )

    async def get_all_tickers(self) -> list[Ticker]:
        data = await self._get(f"{self._base_url}/market/tickers")
        tickers = []
        for d in data.get("data", []):
            sym_raw = d.get("symbol", "")
            if not sym_raw.endswith("usdt"):
                continue
            sym = sym_raw.upper()
            try:
                last = float(d.get("close", 0))
                if last == 0:
                    continue
                open_price = float(d.get("open", last))
                change = last - open_price
                change_pct = (change / open_price * 100) if open_price else 0
                tickers.append(Ticker(
                    symbol=sym,
                    last_price=last,
                    bid=float(d.get("bid", last)),
                    ask=float(d.get("ask", last)),
                    volume_24h=float(d.get("vol", 0)),
                    price_change_24h=change,
                    price_change_pct_24h=change_pct,
                    high_24h=float(d.get("high", last)),
                    low_24h=float(d.get("low", last)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return tickers

    async def get_funding_rate(self, symbol: str) -> FundingRate | None:
        try:
            # HTX linear swap: contract_code = BTC-USDT
            contract = symbol.upper().replace("USDT", "-USDT")
            data = await self._get(f"{self._futures_url}/linear-swap-api/v1/swap_funding_rate", {
                "contract_code": contract,
            })
            if data.get("data"):
                d = data["data"]
                return FundingRate(
                    symbol=symbol,
                    rate=float(d.get("funding_rate", 0)),
                    next_funding_time=datetime.datetime.fromtimestamp(
                        int(d["next_funding_time"]) / 1000, tz=datetime.timezone.utc
                    ) if d.get("next_funding_time") else None,
                )
        except Exception:
            pass
        return None

    async def get_open_interest(self, symbol: str) -> OpenInterest | None:
        try:
            contract = symbol.upper().replace("USDT", "-USDT")
            data = await self._get(f"{self._futures_url}/linear-swap-api/v1/swap_open_interest", {
                "contract_code": contract,
            })
            if data.get("data") and isinstance(data["data"], list) and data["data"]:
                d = data["data"][0]
                return OpenInterest(
                    symbol=symbol,
                    open_interest=float(d.get("volume", 0)),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
        except Exception:
            pass
        return None

    async def get_symbols(self) -> list[str]:
        data = await self._get(f"{self._base_url}/v2/settings/common/symbols")
        symbols = []
        for s in data.get("data", []):
            sym = s.get("sc", "")
            if sym.endswith("usdt") and s.get("te"):
                symbols.append(sym.upper())
        return symbols

    async def close(self):
        await self._client.aclose()
