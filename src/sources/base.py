"""Base class for all source fetchers."""

from abc import ABC, abstractmethod
from typing import Optional
from src.models import InfoItem
from config import config


class SourceFetcher(ABC):
    """Abstract base for a single data source."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier, e.g. 'hacker_news'."""
        pass

    @abstractmethod
    def fetch(self) -> list[InfoItem]:
        """Fetch items from this source. Return empty list on failure."""
        pass

    def _make_request(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """Helper: GET url, return text or None on failure."""
        import requests
        h = {"User-Agent": config.user_agent}
        if headers:
            h.update(headers)
        try:
            r = requests.get(url, headers=h, timeout=config.request_timeout)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"[{self.source_name}] HTTP error: {e}")
            return None
