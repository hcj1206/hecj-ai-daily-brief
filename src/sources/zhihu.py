"""Fetcher for Zhihu (知乎) content via RSSHub."""

import logging
import feedparser

from src.sources.base import SourceFetcher
from src.models import InfoItem

logger = logging.getLogger(__name__)

RSS_URLS = [
    "https://rsshub.app/zhihu/hotlist",
    "https://rsshub.app/zhihu/topics/19776749",  # AI topic
]


class ZhihuFetcher(SourceFetcher):
    """Fetch Zhihu hot topics and AI-related content via RSSHub."""

    @property
    def source_name(self) -> str:
        return "zhihu"

    def fetch(self) -> list[InfoItem]:
        items = []
        for rss_url in RSS_URLS:
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    desc = entry.get("summary", title)[:150]
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=0,
                    ))
            except Exception as e:
                logger.warning("[zhihu] RSS error for %s: %s", rss_url, e)
                continue
        logger.info("[zhihu] Fetched %d items", len(items))
        return items
