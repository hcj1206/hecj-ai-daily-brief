"""Fetcher for Hacker News top stories filtered by AI relevance."""

import json
import logging

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config

logger = logging.getLogger(__name__)

# Keywords used to identify AI/tech-relevant stories
RELEVANCE_KEYWORDS = [
    "ai", "llm", "gpt", "openai", "anthropic", "claude", "gemini",
    "machine learning", "deep learning", "neural", "transformer",
    "copilot", "agent", "language model", "diffusion", "stable diffusion",
    "yolo", "computer vision", "nlp", "rag", "vector", "embedding",
    "fine-tune", "finetune", "hugging face", "pytorch", "tensorflow",
    "dev tool", "code", "programming", "startup", "product",
    "cursor", "windsurf", "devin", "replit",
]


class HackerNewsFetcher(SourceFetcher):
    """Fetch top stories from Hacker News and filter for AI relevance."""

    @property
    def source_name(self) -> str:
        return "hacker_news"

    def fetch(self) -> list[InfoItem]:
        items = []
        text = self._make_request(
            "https://hacker-news.firebaseio.com/v0/topstories.json"
        )
        if not text:
            return items

        try:
            story_ids = json.loads(text)[:config.max_items_per_source]
        except (json.JSONDecodeError, TypeError):
            return items

        for sid in story_ids:
            details = self._make_request(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            )
            if not details:
                continue
            try:
                story = json.loads(details)
                title = story.get("title", "")
                url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
                desc = story.get("title", "")[:150]
                score = story.get("score", 0)
                if self._is_relevant(title, desc):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=score,
                    ))
            except json.JSONDecodeError:
                continue

        logger.info("[hacker_news] Fetched %d relevant items", len(items))
        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        text = f"{title} {desc}".lower()
        return any(kw in text for kw in RELEVANCE_KEYWORDS)
