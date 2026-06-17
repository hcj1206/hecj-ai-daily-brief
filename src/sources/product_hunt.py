"""Fetcher for Product Hunt products, filtered by AI relevance."""

import logging
from datetime import datetime, timedelta

import requests

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config

logger = logging.getLogger(__name__)

AI_TOPICS = {
    "ai", "artificial intelligence", "machine learning",
    "llm", "chatgpt", "developer tools", "open source",
    "productivity", "automation",
}

TITLE_KEYWORDS = [
    "ai", "gpt", "llm", "chat", "copilot", "agent", "intelligence",
    "neural", "deep learning", "machine learning", "automation",
    "no code", "nocode", "workflow",
]


class ProductHuntFetcher(SourceFetcher):
    """Fetch AI-related products from Product Hunt."""

    @property
    def source_name(self) -> str:
        return "product_hunt"

    def fetch(self) -> list[InfoItem]:
        items = []
        if not config.product_hunt_token:
            logger.info("[product_hunt] No API token configured, skipping")
            return items

        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        query = """
        {
          posts(order: VOTES, postedAfter: "%s", first: 20) {
            edges {
              node {
                name
                tagline
                url
                votesCount
                topics { edges { node { name } } }
              }
            }
          }
        }
        """ % yesterday

        headers = {
            "Authorization": f"Bearer {config.product_hunt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            r = requests.post(
                "https://api.producthunt.com/v2/api/graphql",
                json={"query": query},
                headers=headers,
                timeout=config.request_timeout,
            )
            r.raise_for_status()
            data = r.json()
            for edge in data.get("data", {}).get("posts", {}).get("edges", []):
                node = edge.get("node", {})
                title = node.get("name", "")
                tagline = node.get("tagline", "")
                url = node.get("url", "")
                score = node.get("votesCount", 0)
                topics = {
                    t.get("node", {}).get("name", "").lower()
                    for t in node.get("topics", {}).get("edges", [])
                }
                if topics & AI_TOPICS or self._title_suggests_ai(title):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=tagline[:150],
                        score=score,
                    ))
        except Exception as e:
            logger.error("[product_hunt] API error: %s", e)
        logger.info("[product_hunt] Fetched %d items", len(items))
        return items

    @staticmethod
    def _title_suggests_ai(title: str) -> bool:
        return any(k in title.lower() for k in TITLE_KEYWORDS)
