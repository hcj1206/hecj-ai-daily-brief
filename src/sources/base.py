"""Base class for all source fetchers."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests

from config import config
from src.models import InfoItem

logger = logging.getLogger(__name__)


class SourceFetcher(ABC):
    """Abstract base for a single data source."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier, e.g. 'hacker_news'."""
        ...

    @abstractmethod
    def fetch(self) -> list[InfoItem]:
        """Fetch items from this source. Return empty list on failure."""
        ...

    def _make_request(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """GET url, return response text or None on failure."""
        h: dict[str, str] = {"User-Agent": config.user_agent}
        if headers:
            h.update(headers)
        try:
            r = requests.get(url, headers=h, timeout=config.request_timeout)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            logger.warning("[%s] HTTP error fetching %s: %s", self.source_name, url, e)
            return None
