"""Fetcher for Hugging Face daily papers."""

import json
import logging

from src.sources.base import SourceFetcher
from src.models import InfoItem

logger = logging.getLogger(__name__)


class HuggingFaceFetcher(SourceFetcher):
    """Fetch daily papers from Hugging Face."""

    @property
    def source_name(self) -> str:
        return "huggingface"

    def fetch(self) -> list[InfoItem]:
        items = []
        text = self._make_request(
            "https://huggingface.co/api/daily_papers?limit=15"
        )
        if not text:
            return items
        try:
            papers = json.loads(text)
            for paper in papers:
                title = paper.get("title", "")
                paper_id = paper.get("id", "")
                url = f"https://huggingface.co/papers/{paper_id}"
                desc = paper.get("summary", title)[:150]
                score = paper.get("upvotes", 0) or 0
                items.append(InfoItem(
                    title=title,
                    url=url,
                    source=self.source_name,
                    description=desc,
                    score=score,
                ))
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("[huggingface] Parse error: %s", e)
        logger.info("[huggingface] Fetched %d papers", len(items))
        return items
