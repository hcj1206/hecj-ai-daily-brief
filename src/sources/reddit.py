"""Fetcher for AI-focused subreddits."""

import json
import logging

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config

logger = logging.getLogger(__name__)

SUBREDDITS = ["AITools", "artificial", "MachineLearning", "SideProject"]


class RedditFetcher(SourceFetcher):
    """Fetch hot posts from AI/tech subreddits."""

    @property
    def source_name(self) -> str:
        return "reddit"

    def fetch(self) -> list[InfoItem]:
        items = []
        for sub in SUBREDDITS:
            items.extend(self._fetch_subreddit(sub))

        seen = set()
        unique = []
        for item in sorted(items, key=lambda x: x.score, reverse=True):
            if item.title not in seen:
                seen.add(item.title)
                unique.append(item)
        logger.info("[reddit] Fetched %d unique items from %d subreddits",
                     len(unique), len(SUBREDDITS))
        return unique[:config.max_items_per_source]

    def _fetch_subreddit(self, sub: str) -> list[InfoItem]:
        items = []
        text = self._make_request(
            f"https://www.reddit.com/r/{sub}/hot.json?limit=15",
            headers={"User-Agent": config.user_agent},
        )
        if not text:
            return items
        try:
            data = json.loads(text)
            for post in data.get("data", {}).get("children", []):
                p = post.get("data", {})
                title = p.get("title", "")
                url = p.get("url", "")
                desc = p.get("selftext", title)[:150]
                score = p.get("score", 0)
                items.append(InfoItem(
                    title=title,
                    url=url,
                    source=f"{self.source_name}/{sub}",
                    description=desc,
                    score=score,
                ))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("[reddit/%s] Parse error: %s", sub, e)
        return items
