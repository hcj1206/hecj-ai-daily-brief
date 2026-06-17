"""Fetcher for SSpai (少数派) articles via RSS, filtered by AI relevance."""

import logging
import feedparser

from src.sources.base import SourceFetcher
from src.models import InfoItem

logger = logging.getLogger(__name__)

RELEVANCE_KEYWORDS = [
    "ai", "人工智能", "llm", "大模型", "chatgpt", "gpt", "claude",
    "gemini", "copilot", "agent", "工具", "效率", "自动",
    "app", "应用", "软件", "productivity", "workflow",
]


class SSpaiFetcher(SourceFetcher):
    """Fetch SSpai articles and filter for AI/tech relevance."""

    @property
    def source_name(self) -> str:
        return "sspai"

    def fetch(self) -> list[InfoItem]:
        items = []
        try:
            feed = feedparser.parse("https://sspai.com/feed")
            for entry in feed.entries[:15]:
                title = entry.get("title", "")
                url = entry.get("link", "")
                desc = entry.get("summary", title)[:150]
                if self._is_relevant(title, desc):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=0,
                    ))
        except Exception as e:
            logger.error("[sspai] RSS error: %s", e)
        logger.info("[sspai] Fetched %d items", len(items))
        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        text = f"{title} {desc}".lower()
        return any(k in text.lower() for k in RELEVANCE_KEYWORDS)
