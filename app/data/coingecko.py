"""CoinGecko API integration for market data, coin info, and global metrics."""

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings


class CoinGeckoClient:
    def __init__(self):
        self._base_url = settings.COINGECKO_BASE_URL
        headers = {"Accept": "application/json"}
        if settings.COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY
        self._client = httpx.AsyncClient(
            timeout=15.0, headers=headers, follow_redirects=True
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = await self._client.get(f"{self._base_url}{path}", params=params)
        if resp.status_code == 429:
            import asyncio
            await asyncio.sleep(30)
            raise Exception("Rate limited")
        resp.raise_for_status()
        return resp.json()

    async def get_coin_list(self) -> list[dict]:
        """Returns list of all coins with id, symbol, name."""
        return await self._get("/coins/list")

    async def get_coin_data(self, coin_id: str) -> dict:
        """Get detailed coin data including description, links, market data."""
        return await self._get(f"/coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        })

    async def get_market_data(
        self,
        vs_currency: str = "usd",
        per_page: int = 100,
        page: int = 1,
        order: str = "market_cap_desc",
        sparkline: bool = False,
        price_change_pct: str = "1h,24h,7d,30d",
    ) -> list[dict]:
        """Get market data for top coins."""
        return await self._get("/coins/markets", {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": str(sparkline).lower(),
            "price_change_percentage": price_change_pct,
        })

    async def get_trending(self) -> dict:
        """Get trending coins (top-7 by search volume)."""
        return await self._get("/search/trending")

    async def get_global_data(self) -> dict:
        """Get global crypto market data (total market cap, volume, dominance)."""
        data = await self._get("/global")
        return data.get("data", {})

    async def get_fear_greed_index(self) -> dict | None:
        """Try to get fear & greed index from alternative.me."""
        try:
            resp = await self._client.get("https://api.alternative.me/fng/?limit=1")
            if resp.status_code == 200:
                data = resp.json()
                item = data.get("data", [{}])[0]
                return {
                    "value": int(item.get("value", 50)),
                    "classification": item.get("value_classification", "Neutral"),
                }
        except Exception as e:
            logger.debug(f"Fear & Greed fetch failed: {e}")
        return None

    async def get_coin_price_history(
        self, coin_id: str, days: int = 30, vs_currency: str = "usd"
    ) -> dict:
        """Get historical price data for a coin."""
        return await self._get(f"/coins/{coin_id}/market_chart", {
            "vs_currency": vs_currency,
            "days": days,
        })

    async def search_coins(self, query: str) -> list[dict]:
        """Search coins by name or symbol."""
        data = await self._get("/search", {"query": query})
        return data.get("coins", [])

    async def get_coin_logo_url(self, coin_id: str) -> str | None:
        """Get logo URL for a coin."""
        try:
            data = await self.get_coin_data(coin_id)
            return data.get("image", {}).get("small")
        except Exception:
            return None

    async def close(self):
        await self._client.aclose()


coingecko = CoinGeckoClient()
