"""Alpha feed — aggregates signals from news, social sentiment, on-chain, new listings."""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from loguru import logger

from app.data.coingecko import coingecko
from app.data.dexscreener import dexscreener
from app.data.news_parser import news_parser


@dataclass
class AlphaEvent:
    source: str
    event_type: str  # trending, new_listing, volume_surge, news_sentiment, fear_greed
    coin_symbol: str | None
    title: str
    description: str
    importance: float  # 0.0 to 1.0
    url: str | None = None
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlphaFeed:
    """Aggregates alpha from multiple data sources into a unified feed."""

    async def get_trending_alpha(self) -> list[AlphaEvent]:
        """Get trending coins from CoinGecko."""
        events = []
        try:
            data = await coingecko.get_trending()
            coins = data.get("coins", [])
            for coin_data in coins:
                item = coin_data.get("item", {})
                events.append(AlphaEvent(
                    source="CoinGecko",
                    event_type="trending",
                    coin_symbol=item.get("symbol", "").upper(),
                    title=f"🔥 Trending: {item.get('name', 'Unknown')} ({item.get('symbol', '')})",
                    description=f"Market cap rank: #{item.get('market_cap_rank', 'N/A')}",
                    importance=0.6,
                    data={"coin_id": item.get("id"), "market_cap_rank": item.get("market_cap_rank")},
                ))
        except Exception as e:
            logger.error(f"Trending alpha fetch failed: {e}")
        return events

    async def get_new_dex_listings(self) -> list[AlphaEvent]:
        """Find new high-potential DEX listings."""
        events = []
        try:
            new_pairs = await dexscreener.analyze_new_pairs(min_liquidity=10000, min_volume=5000)
            for pair in new_pairs[:10]:
                base = pair.get("base_token", {})
                symbol = base.get("symbol", "???")
                name = base.get("name", "Unknown")
                events.append(AlphaEvent(
                    source="DexScreener",
                    event_type="new_listing",
                    coin_symbol=symbol.upper(),
                    title=f"🆕 New DEX Listing: {name} ({symbol})",
                    description=(
                        f"Chain: {pair.get('chain', '?')} | DEX: {pair.get('dex', '?')}\n"
                        f"Liquidity: ${pair.get('liquidity_usd', 0):,.0f} | "
                        f"Vol 24h: ${pair.get('volume_24h', 0):,.0f}"
                    ),
                    importance=0.5,
                    url=pair.get("url"),
                    data=pair,
                ))
        except Exception as e:
            logger.error(f"DEX listing alpha failed: {e}")
        return events

    async def get_market_movers(self) -> list[AlphaEvent]:
        """Detect big market moves from top coins."""
        events = []
        try:
            market = await coingecko.get_market_data(per_page=100)
            for coin in market:
                pct_1h = coin.get("price_change_percentage_1h_in_currency") or 0
                pct_24h = coin.get("price_change_percentage_24h_in_currency") or 0
                symbol = coin.get("symbol", "").upper()

                # Detect 1h surge/dump
                if abs(pct_1h) >= 5:
                    direction = "surge" if pct_1h > 0 else "dump"
                    events.append(AlphaEvent(
                        source="CoinGecko",
                        event_type="volume_surge",
                        coin_symbol=symbol,
                        title=f"{'🚀' if pct_1h > 0 else '💥'} {symbol} 1h {direction}: {pct_1h:+.1f}%",
                        description=f"24h: {pct_24h:+.1f}% | MCap: #{coin.get('market_cap_rank', '?')}",
                        importance=min(0.9, 0.5 + abs(pct_1h) / 20),
                        data={
                            "price": coin.get("current_price"),
                            "pct_1h": pct_1h,
                            "pct_24h": pct_24h,
                            "volume": coin.get("total_volume"),
                        },
                    ))

                # Detect 24h big moves
                if abs(pct_24h) >= 15:
                    direction = "rally" if pct_24h > 0 else "crash"
                    events.append(AlphaEvent(
                        source="CoinGecko",
                        event_type="volume_surge",
                        coin_symbol=symbol,
                        title=f"{'📈' if pct_24h > 0 else '📉'} {symbol} 24h {direction}: {pct_24h:+.1f}%",
                        description=f"Price: ${coin.get('current_price', 0):,.4f}",
                        importance=min(0.9, 0.6 + abs(pct_24h) / 50),
                        data={
                            "price": coin.get("current_price"),
                            "pct_24h": pct_24h,
                            "volume": coin.get("total_volume"),
                        },
                    ))
        except Exception as e:
            logger.error(f"Market movers alpha failed: {e}")
        return events

    async def get_fear_greed_alpha(self) -> AlphaEvent | None:
        """Get Fear & Greed index as alpha signal."""
        try:
            fg = await coingecko.get_fear_greed_index()
            if fg:
                value = fg["value"]
                classification = fg["classification"]
                importance = 0.3
                if value <= 20 or value >= 80:
                    importance = 0.8
                elif value <= 30 or value >= 70:
                    importance = 0.6

                return AlphaEvent(
                    source="Alternative.me",
                    event_type="fear_greed",
                    coin_symbol=None,
                    title=f"🧭 Fear & Greed Index: {value} ({classification})",
                    description=(
                        "Extreme Fear = potential buy zone\n"
                        "Extreme Greed = potential sell zone"
                        if value <= 25 or value >= 75
                        else f"Market sentiment: {classification}"
                    ),
                    importance=importance,
                    data=fg,
                )
        except Exception as e:
            logger.error(f"Fear & Greed alpha failed: {e}")
        return None

    async def get_full_alpha_feed(self) -> list[AlphaEvent]:
        """Aggregate all alpha sources into a single feed, sorted by importance."""
        import asyncio
        results = await asyncio.gather(
            self.get_trending_alpha(),
            self.get_new_dex_listings(),
            self.get_market_movers(),
            self.get_fear_greed_alpha(),
            return_exceptions=True,
        )

        all_events = []
        for result in results:
            if isinstance(result, list):
                all_events.extend(result)
            elif isinstance(result, AlphaEvent):
                all_events.append(result)

        # Sort by importance descending
        all_events.sort(key=lambda e: e.importance, reverse=True)
        return all_events


alpha_feed = AlphaFeed()
