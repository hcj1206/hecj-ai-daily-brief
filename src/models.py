"""Data models for the daily brief system."""

from dataclasses import dataclass, field


@dataclass
class InfoItem:
    """Unified data item from any source."""
    title: str
    url: str
    source: str          # e.g. "hacker_news", "product_hunt"
    description: str     # 150 chars max summary
    score: int = 0       # popularity/score for sorting
    published: str = ""  # "2025-06-17" format


@dataclass
class BriefResult:
    """Result from the AI summarizer."""
    raw_count: int = 0
    summarized_items: list = field(default_factory=list)
    summary_text: str = ""
    error: str = ""
