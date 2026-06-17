"""Global configuration for AI Daily Brief."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # API Keys (read from environment variables)
    deepseek_api_key: str = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY", "")
    )
    wxpusher_token: str = field(
        default_factory=lambda: os.environ.get("WXPUSHER_TOKEN", "")
    )
    wxpusher_uid: str = field(
        default_factory=lambda: os.environ.get("WXPUSHER_UID", "")
    )

    # Product Hunt
    product_hunt_token: str = field(
        default_factory=lambda: os.environ.get("PRODUCT_HUNT_TOKEN", "")
    )

    # Source toggles
    enable_product_hunt: bool = True
    enable_hacker_news: bool = True
    enable_reddit: bool = True
    enable_github_trending: bool = True
    enable_huggingface: bool = True
    enable_zhihu: bool = True
    enable_sspai: bool = True
    enable_jike: bool = True

    # Fetch limits per source
    max_items_per_source: int = 20

    # DeepSeek
    deepseek_model: str = "deepseek-chat"
    deepseek_max_tokens: int = 1024
    deepseek_temperature: float = 0.3

    # WxPusher
    wxpusher_api_url: str = "https://wxpusher.zjiecode.com/api/send/message"

    # HTTP
    request_timeout: int = 15
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


config = Config()
