#!/usr/bin/env python3
"""AI Daily Brief — Main entry point.

Orchestrates: fetch from all sources → summarize → push to WeChat.
"""

import logging
import sys
from datetime import datetime, timezone, timedelta

# Ensure the project root is on sys.path so config can be imported
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from src.models import InfoItem
from src.summarizer import Summarizer
from src.wechat_publisher import WeChatPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

CST = timezone(timedelta(hours=8))


def get_enabled_fetchers() -> list:
    """Return a list of fetcher instances for enabled sources."""
    fetchers = []
    try:
        from src.sources.hacker_news import HackerNewsFetcher
        from src.sources.reddit import RedditFetcher
        from src.sources.product_hunt import ProductHuntFetcher
        from src.sources.huggingface import HuggingFaceFetcher
        from src.sources.github_trending import GitHubTrendingFetcher
        from src.sources.zhihu import ZhihuFetcher
        from src.sources.sspai import SSpaiFetcher
        from src.sources.jike import JikeFetcher
    except ImportError as e:
        logger.error("Failed to import fetchers: %s", e)
        return fetchers

    mapping = [
        (config.enable_hacker_news, HackerNewsFetcher),
        (config.enable_reddit, RedditFetcher),
        (config.enable_product_hunt, ProductHuntFetcher),
        (config.enable_huggingface, HuggingFaceFetcher),
        (config.enable_github_trending, GitHubTrendingFetcher),
        (config.enable_zhihu, ZhihuFetcher),
        (config.enable_sspai, SSpaiFetcher),
        (config.enable_jike, JikeFetcher),
    ]
    for enabled, cls in mapping:
        if enabled:
            fetchers.append(cls())
    return fetchers


def run():
    """Main pipeline: fetch → dedup → summarize → push."""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("AI Daily Brief started at %s", now)

    # 1. Fetch from all enabled sources
    all_items: list[InfoItem] = []
    fetchers = get_enabled_fetchers()
    logger.info("Found %d enabled fetchers", len(fetchers))

    for fetcher in fetchers:
        logger.info("Fetching from %s...", fetcher.source_name)
        try:
            items = fetcher.fetch()
            logger.info("  → got %d items", len(items))
            all_items.extend(items)
        except Exception as e:
            logger.error("  → error from %s: %s", fetcher.source_name, e)

    # 2. Deduplicate by title, sort by score descending
    seen_titles = set()
    unique_items = []
    for item in sorted(all_items, key=lambda x: x.score, reverse=True):
        if item.title not in seen_titles:
            seen_titles.add(item.title)
            unique_items.append(item)

    unique_items = unique_items[:50]
    logger.info("%d unique items after dedup and capping", len(unique_items))

    # 3. Summarize with DeepSeek
    summarizer = Summarizer()
    brief = summarizer.summarize(unique_items)

    # 4. Publish to WeChat Official Account as draft
    publisher = WeChatPublisher()
    success = publisher.publish(brief)
    logger.info("WeChat publish %s", "succeeded" if success else "failed")

    # 5. Print brief to stdout (visible in GitHub Actions logs)
    if brief.summary_text:
        print("\n" + "=" * 40)
        print("BRIEF CONTENT:")
        print("=" * 40)
        print(brief.summary_text)
        print("=" * 40)

    return success


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
