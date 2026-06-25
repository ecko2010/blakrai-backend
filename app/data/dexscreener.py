"""DexScreener API integration — detect new tokens, DEX pairs, trends."""

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings


class DexScreenerClient:
    def __init__(self):
        self._base_url = settings.DEXSCREENER_BASE_URL
        self._client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = await self._client.get(f"{self._base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_pairs(self, query: str) -> list[dict]:
        """Search for pairs by token name, symbol, or address."""
        data = await self._get(f"/dex/search", {"q": query})
        return data.get("pairs", [])

    async def get_pair(self, chain_id: str, pair_address: str) -> dict | None:
        """Get specific pair data."""
        data = await self._get(f"/dex/pairs/{chain_id}/{pair_address}")
        pairs = data.get("pairs", [])
        return pairs[0] if pairs else None

    async def get_token_pairs(self, token_address: str) -> list[dict]:
        """Get all pairs for a specific token across chains."""
        data = await self._get(f"/dex/tokens/{token_address}")
        return data.get("pairs", [])

    async def get_latest_boosted(self) -> list[dict]:
        """Get tokens with active boosts (promoted tokens)."""
        try:
            data = await self._get("/token-boosts/latest/v1")
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.debug(f"DexScreener boosted tokens failed: {e}")
            return []

    async def get_trending_tokens(self) -> list[dict]:
        """Get trending tokens from DexScreener."""
        try:
            resp = await self._client.get(
                "https://api.dexscreener.com/token-boosts/top/v1",
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json() if isinstance(resp.json(), list) else []
        except Exception as e:
            logger.debug(f"DexScreener trending failed: {e}")
        return []

    async def analyze_new_pairs(self, min_liquidity: float = 10000, min_volume: float = 5000) -> list[dict]:
        """Find new pairs that meet minimum liquidity and volume thresholds."""
        try:
            latest = await self.get_latest_boosted()
            filtered = []
            for token in latest:
                pairs = await self.search_pairs(token.get("tokenAddress", ""))
                for pair in pairs:
                    liq = pair.get("liquidity", {}).get("usd", 0) or 0
                    vol = pair.get("volume", {}).get("h24", 0) or 0
                    if liq >= min_liquidity and vol >= min_volume:
                        filtered.append({
                            "pair_address": pair.get("pairAddress"),
                            "base_token": pair.get("baseToken", {}),
                            "quote_token": pair.get("quoteToken", {}),
                            "chain": pair.get("chainId"),
                            "dex": pair.get("dexId"),
                            "price_usd": pair.get("priceUsd"),
                            "liquidity_usd": liq,
                            "volume_24h": vol,
                            "price_change_5m": pair.get("priceChange", {}).get("m5"),
                            "price_change_1h": pair.get("priceChange", {}).get("h1"),
                            "price_change_24h": pair.get("priceChange", {}).get("h24"),
                            "created_at": pair.get("pairCreatedAt"),
                            "url": pair.get("url"),
                        })
            return filtered
        except Exception as e:
            logger.error(f"DexScreener new pair analysis failed: {e}")
            return []

    async def close(self):
        await self._client.aclose()


dexscreener = DexScreenerClient()
