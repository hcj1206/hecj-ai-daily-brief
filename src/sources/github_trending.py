"""Fetcher for GitHub trending repositories filtered by AI relevance."""

import logging
import re

from bs4 import BeautifulSoup

from src.sources.base import SourceFetcher
from src.models import InfoItem

logger = logging.getLogger(__name__)

RELEVANCE_KEYWORDS = [
    "ai", "llm", "gpt", "openai", "anthropic", "claude", "gemini",
    "machine learning", "deep learning", "neural", "transformer",
    "rag", "agent", "copilot", "embedding", "vector",
    "diffusion", "stable diffusion", "langchain", "llamaindex",
    "autogpt", "pytorch", "tensorflow", "huggingface",
    "chat", "chatbot", "fine-tune", "finetune",
    "yolo", "object detection", "ocr",
    "dev tool", "cli", "code", "programming",
]


class GitHubTrendingFetcher(SourceFetcher):
    """Fetch trending GitHub repos and filter for AI relevance."""

    @property
    def source_name(self) -> str:
        return "github_trending"

    def fetch(self) -> list[InfoItem]:
        items = []
        text = self._make_request("https://github.com/trending?since=daily")
        if not text:
            return items
        try:
            soup = BeautifulSoup(text, "lxml")
            articles = soup.select("article.Box-row")
            for article in articles:
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                full_name = h2.get("href", "").strip("/")
                title = full_name
                url = f"https://github.com/{full_name}"

                desc_el = article.select_one("p")
                desc = desc_el.get_text(strip=True)[:150] if desc_el else ""

                stars_el = article.select_one(".d-inline-block.float-sm-right")
                score = 0
                if stars_el:
                    stars_text = stars_el.get_text(strip=True).replace(",", "")
                    try:
                        score = int(stars_text)
                    except ValueError:
                        pass

                if self._is_relevant(title, desc):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=score,
                    ))
        except Exception as e:
            logger.error("[github_trending] Parse error: %s", e)
        logger.info("[github_trending] Fetched %d items", len(items))
        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        text = f"{title} {desc}".lower()
        return any(kw in text.lower() for kw in RELEVANCE_KEYWORDS)
