"""RSS news parser for crypto news feeds — alpha feed aggregation."""

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import NewsItem


# Curated list of top crypto RSS feeds
DEFAULT_FEEDS: list[dict[str, str]] = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss"},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed"},
    {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/"},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/.rss/full/"},
    {"name": "Blockworks", "url": "https://blockworks.co/feed"},
    {"name": "DeFi Pulse", "url": "https://defipulse.com/blog/feed/"},
]


class NewsParser:
    def __init__(self, feeds: list[dict[str, str]] | None = None):
        self.feeds = feeds or DEFAULT_FEEDS
        self._client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

    async def fetch_feed(self, feed_info: dict[str, str]) -> list[dict[str, Any]]:
        """Fetch and parse a single RSS feed."""
        try:
            resp = await self._client.get(feed_info["url"])
            if resp.status_code != 200:
                logger.warning(f"Feed {feed_info['name']} returned {resp.status_code}")
                return []

            parsed = feedparser.parse(resp.text)
            articles = []
            for entry in parsed.entries[:30]:  # limit per feed
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Clean HTML from summary
                if summary:
                    from html import unescape
                    import re
                    summary = unescape(re.sub(r"<[^>]+>", "", summary))[:500]

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        published = datetime.now(timezone.utc)

                if not title or not link:
                    continue

                articles.append({
                    "source": feed_info["name"],
                    "source_url": feed_info["url"],
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "published_at": published or datetime.now(timezone.utc),
                })
            return articles
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_info['name']}: {e}")
            return []

    async def fetch_all_feeds(self) -> list[dict[str, Any]]:
        """Fetch all RSS feeds concurrently."""
        tasks = [self.fetch_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        # Sort by date descending
        all_articles.sort(key=lambda x: x.get("published_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return all_articles

    async def save_new_articles(self) -> int:
        """Fetch all feeds and save only new (unseen) articles to DB."""
        articles = await self.fetch_all_feeds()
        saved_count = 0
        async with async_session() as session:
            for article in articles:
                # Check if article URL already exists
                existing = await session.execute(
                    select(NewsItem.id).where(NewsItem.url == article["url"]).limit(1)
                )
                if existing.scalar_one_or_none() is not None:
                    continue

                news_item = NewsItem(
                    source=article["source"],
                    source_url=article["source_url"],
                    title=article["title"],
                    summary=article.get("summary"),
                    url=article["url"],
                    is_processed=False,
                )
                session.add(news_item)
                saved_count += 1

            if saved_count > 0:
                await session.commit()
                logger.info(f"Saved {saved_count} new articles")
        return saved_count

    def add_feed(self, name: str, url: str):
        """Dynamically add a new RSS feed."""
        self.feeds.append({"name": name, "url": url})

    def remove_feed(self, name: str):
        """Remove a feed by name."""
        self.feeds = [f for f in self.feeds if f["name"] != name]

    async def close(self):
        await self._client.aclose()


news_parser = NewsParser()
