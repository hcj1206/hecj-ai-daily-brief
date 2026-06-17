"""Fetcher for Jike (即刻) content via RSSHub."""

import logging
import feedparser

from src.sources.base import SourceFetcher
from src.models import InfoItem

logger = logging.getLogger(__name__)

RSS_URLS = [
    "https://rsshub.app/jike/topic/5538b6d3b09bbd3a440b3df8",  # AI topic
]


class JikeFetcher(SourceFetcher):
    """Fetch Jike posts via RSSHub public instance."""

    @property
    def source_name(self) -> str:
        return "jike"

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
                logger.warning("[jike] RSS error for %s: %s", rss_url, e)
                continue
        logger.info("[jike] Fetched %d items", len(items))
        return items
