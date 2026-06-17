# AI Daily Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily AI tool news briefing system that scrapes 8+ platforms, generates a Chinese summary via DeepSeek, and pushes it to WeChat via WxPusher.

**Architecture:** Python pipeline running on GitHub Actions (cron: daily 09:00 CST). Each data source is a separate fetcher class implementing a common interface. Fetched items are aggregated, summarized by DeepSeek API, then pushed to WeChat through WxPusher.

**Tech Stack:** Python 3.11+, requests, feedparser, beautifulsoup4, DeepSeek API, WxPusher API, GitHub Actions.

---

### Task 1: Project Scaffolding and Configuration

**Files:**
- Create: `config.py`
- Create: `requirements.txt`
- Create: `.github/workflows/daily-brief.yml`

- [ ] **Step 1: Create `config.py`**

This file holds all non-sensitive configuration (sensitive values come from environment variables via GitHub Secrets).

```python
"""Global configuration for AI Daily Brief."""

import os
from dataclasses import dataclass, field
from typing import Optional


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
```

- [ ] **Step 2: Create `requirements.txt`**

```
requests>=2.31.0
feedparser>=6.0.11
beautifulsoup4>=4.12.2
lxml>=5.1.0
```

- [ ] **Step 3: Create `.github/workflows/daily-brief.yml`**

```yaml
name: Daily AI Brief

on:
  schedule:
    # UTC 01:00 = CST 09:00
    - cron: '0 1 * * *'
  workflow_dispatch:  # allow manual trigger for testing

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily brief
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          WXPUSHER_TOKEN: ${{ secrets.WXPUSHER_TOKEN }}
          WXPUSHER_UID: ${{ secrets.WXPUSHER_UID }}
          PRODUCT_HUNT_TOKEN: ${{ secrets.PRODUCT_HUNT_TOKEN }}
        run: python src/main.py
```

---

### Task 2: Data Models and Base Fetcher

**Files:**
- Create: `src/__init__.py` (empty)
- Create: `src/models.py`
- Create: `src/sources/__init__.py`
- Create: `src/sources/base.py`

- [ ] **Step 1: Create `src/__init__.py`**

Empty file.

- [ ] **Step 2: Create `src/models.py`**

```python
"""Data models for the daily brief system."""

from dataclasses import dataclass, field
from datetime import datetime


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
```

- [ ] **Step 3: Create `src/sources/__init__.py`**

```python
# Source fetchers package
```

- [ ] **Step 4: Create `src/sources/base.py`**

```python
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
```

---

### Task 3: Hacker News Source

**Files:**
- Create: `src/sources/hacker_news.py`

- [ ] **Step 1: Create `src/sources/hacker_news.py`**

```python
"""Fetcher for Hacker News top stories."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config
import json


class HackerNewsFetcher(SourceFetcher):

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
                # Only keep stories with AI/tech keywords
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

        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        keywords = [
            "ai", "llm", "gpt", "openai", "anthropic", "claude", "gemini",
            "machine learning", "deep learning", "neural", "transformer",
            "copilot", "agent", "language model", "diffusion", "stable diffusion",
            "yolo", "computer vision", "nlp", "rag", "vector", "embedding",
            "fine-tune", "finetune", "hugging face", "pytorch", "tensorflow",
            "dev tool", "code", "programming", "startup", "product",
        ]
        text = f"{title} {desc}".lower()
        return any(kw in text for kw in keywords)
```

---

### Task 4: Reddit Source

**Files:**
- Create: `src/sources/reddit.py`

- [ ] **Step 1: Create `src/sources/reddit.py`**

```python
"""Fetcher for Reddit AI-focused subreddits."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config
import json


class RedditFetcher(SourceFetcher):
    SUBREDDITS = ["AITools", "artificial", "MachineLearning", "SideProject"]

    @property
    def source_name(self) -> str:
        return "reddit"

    def fetch(self) -> list[InfoItem]:
        items = []
        for sub in self.SUBREDDITS:
            items.extend(self._fetch_subreddit(sub))
        # Deduplicate by title and sort by score
        seen = set()
        unique = []
        for item in sorted(items, key=lambda x: x.score, reverse=True):
            if item.title not in seen:
                seen.add(item.title)
                unique.append(item)
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
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return items
```

---

### Task 5: Product Hunt and Hugging Face Sources

**Files:**
- Create: `src/sources/product_hunt.py`
- Create: `src/sources/huggingface.py`

- [ ] **Step 1: Create `src/sources/product_hunt.py`**

```python
"""Fetcher for Product Hunt featuring AI tools."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config
import json


class ProductHuntFetcher(SourceFetcher):

    @property
    def source_name(self) -> str:
        return "product_hunt"

    def fetch(self) -> list[InfoItem]:
        items = []
        if not config.product_hunt_token:
            print("[product_hunt] No API token configured, skipping")
            return items

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
        """ % self._today_str()

        headers = {
            "Authorization": f"Bearer {config.product_hunt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        import requests
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
                # Check if it's AI-related via topics
                topics = []
                for t in node.get("topics", {}).get("edges", []):
                    topics.append(t.get("node", {}).get("name", "").lower())
                is_ai = any(
                    t in ["ai", "artificial intelligence", "machine learning",
                          "llm", "chatgpt", "developer tools", "open source"]
                    for t in topics
                )
                if is_ai or self._title_suggests_ai(title):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=tagline[:150],
                        score=score,
                    ))
        except Exception as e:
            print(f"[product_hunt] Error: {e}")
        return items

    @staticmethod
    def _today_str() -> str:
        from datetime import datetime, timedelta
        # Product Hunt uses Pacific time; fetch posts from yesterday to be safe
        d = datetime.utcnow() - timedelta(days=1)
        return d.strftime("%Y-%m-%d")

    @staticmethod
    def _title_suggests_ai(title: str) -> bool:
        kw = ["ai", "gpt", "llm", "chat", "copilot", "agent", "intelligence",
              "neural", "deep learning", "machine learning", "automation",
              "no code", "nocode", "workflow"]
        return any(k in title.lower() for k in kw)
```

- [ ] **Step 2: Create `src/sources/huggingface.py`**

```python
"""Fetcher for Hugging Face daily papers."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
import json


class HuggingFaceFetcher(SourceFetcher):

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
                url = f"https://huggingface.co/papers/{paper.get('id', '')}"
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
            print(f"[huggingface] Parse error: {e}")
        return items
```

---

### Task 6: GitHub Trending Source

**Files:**
- Create: `src/sources/github_trending.py`

- [ ] **Step 1: Create `src/sources/github_trending.py`**

```python
"""Fetcher for GitHub trending repositories."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
from config import config
from bs4 import BeautifulSoup


class GitHubTrendingFetcher(SourceFetcher):

    @property
    def source_name(self) -> str:
        return "github_trending"

    def fetch(self) -> list[InfoItem]:
        items = []
        text = self._make_request(
            "https://github.com/trending?since=daily"
        )
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
                    try:
                        score = int(stars_el.get_text(strip=True).replace(",", ""))
                    except ValueError:
                        pass

                # Only keep AI-related repos by description/topic keywords
                if self._is_relevant(title, desc):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=score,
                    ))
        except Exception as e:
            print(f"[github_trending] Parse error: {e}")
        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        keywords = [
            "ai", "llm", "gpt", "openai", "anthropic", "claude", "gemini",
            "machine learning", "deep learning", "neural", "transformer",
            "rag", "agent", "copilot", "embedding", "vector",
            "diffusion", "stable diffusion", "langchain", "llamaindex",
            "autogpt", "pytorch", "tensorflow", "huggingface",
            "chat", "chatbot", "fine-tune", "finetune",
            "yolo", "object detection", "ocr",
            "dev tool", "cli", "code", "programming",
        ]
        text = f"{title} {desc}".lower()
        return any(kw in text for kw in keywords)
```

---

### Task 7: Chinese RSS Sources

**Files:**
- Create: `src/sources/zhihu.py`
- Create: `src/sources/sspai.py`
- Create: `src/sources/jike.py`

- [ ] **Step 1: Create `src/sources/zhihu.py`**

```python
"""Fetcher for Zhihu (知乎) topic feeds via RSSHub."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
import feedparser
from config import config


class ZhihuFetcher(SourceFetcher):
    """Fetches Zhihu content. Uses RSSHub as a proxy for public feeds."""

    RSS_URLS = [
        # RSSHub Zhihu daily hot list (self-hosted or public instance)
        "https://rsshub.app/zhihu/hotlist",
        "https://rsshub.app/zhihu/topics/19776749",  # AI topic
    ]

    @property
    def source_name(self) -> str:
        return "zhihu"

    def fetch(self) -> list[InfoItem]:
        items = []
        for rss_url in self.RSS_URLS:
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    desc = entry.get("summary", title)[:150]
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=0,
                    ))
            except Exception as e:
                print(f"[zhihu] RSS error for {rss_url}: {e}")
                continue
        return items
```

- [ ] **Step 2: Create `src/sources/sspai.py`**

```python
"""Fetcher for SSpai (少数派) articles via RSS."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
import feedparser


class SSpaiFetcher(SourceFetcher):

    @property
    def source_name(self) -> str:
        return "sspai"

    def fetch(self) -> list[InfoItem]:
        items = []
        try:
            feed = feedparser.parse("https://sspai.com/feed")
            for entry in feed.entries[:15]:
                title = entry.get("title", "")
                url = entry.get("link", "")
                desc = entry.get("summary", title)[:150]
                # Filter AI/tech related
                if self._is_relevant(title, desc):
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=0,
                    ))
        except Exception as e:
            print(f"[sspai] RSS error: {e}")
        return items

    @staticmethod
    def _is_relevant(title: str, desc: str) -> bool:
        kw = ["ai", "人工智能", "llm", "大模型", "chatgpt", "gpt", "claude",
              "gemini", "copilot", "agent", "工具", "效率", "自动",
              "app", "应用", "软件", "productivity", "workflow"]
        text = f"{title} {desc}".lower()
        return any(k in text.lower() for k in kw)
```

- [ ] **Step 3: Create `src/sources/jike.py`**

```python
"""Fetcher for Jike (即刻) content. Uses RSSHub as public proxy."""

from src.sources.base import SourceFetcher
from src.models import InfoItem
import feedparser


class JikeFetcher(SourceFetcher):
    """Jike doesn't provide public RSS. Uses RSSHub public instance."""

    RSS_URLS = [
        "https://rsshub.app/jike/topic/5538b6d3b09bbd3a440b3df8",  # AI topic
    ]

    @property
    def source_name(self) -> str:
        return "jike"

    def fetch(self) -> list[InfoItem]:
        items = []
        for rss_url in self.RSS_URLS:
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    desc = entry.get("summary", title)[:150]
                    items.append(InfoItem(
                        title=title,
                        url=url,
                        source=self.source_name,
                        description=desc,
                        score=0,
                    ))
            except Exception as e:
                print(f"[jike] RSS error for {rss_url}: {e}")
                continue
        return items
```

---

### Task 8: Summarizer — DeepSeep API Integration

**Files:**
- Create: `src/summarizer.py`

- [ ] **Step 1: Create `src/summarizer.py`**

```python
"""AI summarizer using DeepSeek API."""

from src.models import InfoItem, BriefResult
from config import config
import json
import requests


class Summarizer:

    def summarize(self, items: list[InfoItem]) -> BriefResult:
        """Send items to DeepSeek and return a structured brief."""
        result = BriefResult(raw_count=len(items))
        if not items:
            result.error = "No items to summarize"
            return result

        prompt = self._build_prompt(items)
        response_text = self._call_deepseek(prompt)

        if not response_text:
            result.error = "DeepSeek API returned no response"
            return result

        result.summary_text = response_text.strip()
        result.summarized_items = items
        return result

    def _build_prompt(self, items: list[InfoItem]) -> str:
        """Build a prompt that asks DeepSeek to create a daily brief."""
        lines = [
            "你是一个 AI 工具资讯编辑。请根据以下当日收集的 AI 工具资讯，",
            "生成一份简洁的每日简报。要求：",
            "1. 每条资讯用一句话概括（不超过50字）",
            "2. 按推荐度从高到低排列",
            "3. 每条末尾标注来源（如 [Product Hunt]）",
            "4. 如果资讯不适合普通开发者阅读可以跳过",
            "5. 最后用 --- 分隔，给出一个今日趋势总结（一句话）",
            "",
            "今日资讯列表：",
        ]
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. [{item.source}] {item.title} — {item.description}"
            )

        return "\n".join(lines)

    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API and return response text."""
        if not config.deepseek_api_key:
            print("[summarizer] No DeepSeek API key configured")
            return ""

        payload = {
            "model": config.deepseek_model,
            "messages": [
                {"role": "system", "content": "你是一个专业的 AI 工具资讯编辑。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": config.deepseek_max_tokens,
            "temperature": config.deepseek_temperature,
        }
        headers = {
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[summarizer] API call failed: {e}")
            return ""
```

---

### Task 9: Pusher — WxPusher Integration

**Files:**
- Create: `src/pusher.py`

- [ ] **Step 1: Create `src/pusher.py`**

```python
"""Push briefing to WeChat via WxPusher."""

from src.models import BriefResult
from config import config
import requests
import json


class Pusher:

    def push(self, brief: BriefResult) -> bool:
        """Push the brief summary to WeChat via WxPusher API."""
        if not config.wxpusher_token:
            print("[pusher] WxPusher token not configured")
            return False

        if brief.error:
            content = f"⚠️ AI Daily Brief - 今日简报生成失败\n\n{brief.error}"
        else:
            date_str = self._today_cst()
            content = (
                f"📡 AI Daily Brief · {date_str}\n\n"
                f"{brief.summary_text}\n\n"
                f"---\n共收录 {brief.raw_count} 条资讯"
            )

        payload = {
            "appToken": config.wxpusher_token,
            "content": content,
            "contentType": 1,  # 1=text, 2=html
            "uids": [config.wxpusher_uid],
        }

        try:
            r = requests.post(
                config.wxpusher_api_url,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            result = r.json()
            if result.get("code") == 1000:
                print(f"[pusher] Push success: {result.get('msg', '')}")
                return True
            else:
                print(f"[pusher] Push API error: {result}")
                return False
        except Exception as e:
            print(f"[pusher] Push failed: {e}")
            return False

    @staticmethod
    def _today_cst() -> str:
        from datetime import datetime, timezone, timedelta
        cst = timezone(timedelta(hours=8))
        return datetime.now(cst).strftime("%Y-%m-%d")
```

---

### Task 10: Main Entry Point (Orchestrator)

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Create `src/main.py`**

```python
#!/usr/bin/env python3
"""AI Daily Brief - Main entry point.

Orchestrates: fetch from all sources -> summarize -> push to WeChat.
"""

from src.models import InfoItem
from src.summarizer import Summarizer
from src.pusher import Pusher
from config import config
from datetime import datetime, timezone, timedelta


def get_enabled_fetchers() -> list:
    """Return a list of fetcher instances based on config toggles."""
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
        print(f"[main] Import error: {e}")
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
    """Main pipeline."""
    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[main] AI Daily Brief started at {now}")

    # 1. Fetch from all sources
    all_items: list[InfoItem] = []
    fetchers = get_enabled_fetchers()
    print(f"[main] Found {len(fetchers)} enabled fetchers")

    for fetcher in fetchers:
        print(f"[main] Fetching from {fetcher.source_name}...")
        try:
            items = fetcher.fetch()
            print(f"[main]   -> got {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"[main]   -> error: {e}")

    # 2. Deduplicate and sort
    seen_titles = set()
    unique_items = []
    for item in sorted(all_items, key=lambda x: x.score, reverse=True):
        if item.title not in seen_titles:
            seen_titles.add(item.title)
            unique_items.append(item)

    # Cap at reasonable amount for summarization
    unique_items = unique_items[:50]
    print(f"[main] {len(unique_items)} unique items after dedup")

    # 3. Summarize
    summarizer = Summarizer()
    brief = summarizer.summarize(unique_items)

    # 4. Push
    pusher = Pusher()
    success = pusher.push(brief)
    print(f"[main] Push {'succeeded' if success else 'failed'}")

    # 5. Print brief to stdout (shows in GitHub Actions logs)
    if brief.summary_text:
        print("\n" + "=" * 40)
        print("BRIEF CONTENT:")
        print("=" * 40)
        print(brief.summary_text)
        print("=" * 40)


if __name__ == "__main__":
    run()
```

---

### Task 11: README and Final Setup

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# AI Daily Brief 📡

每日自动收集 AI 工具资讯，生成精华简报推送到微信。

## 数据源

| 平台 | 方式 | 说明 |
|------|------|------|
| Product Hunt | GraphQL API | AI 分类每日新品 |
| Hacker News | Firebase API | 按关键词过滤 |
| Reddit | JSON API | r/AITools 等子版块 |
| GitHub Trending | 页面解析 | AI 相关热门项目 |
| Hugging Face | 官方 API | 每日论文 |
| 知乎 | RSSHub | 热门/科技话题 |
| 少数派 | RSS | AI 效率工具 |
| 即刻 | RSSHub | AI 圈子动态 |

## 配置

通过 GitHub Secrets 设置以下变量：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 平台 API Key |
| `WXPUSHER_TOKEN` | WxPusher 应用 Token |
| `WXPUSHER_UID` | WxPusher 用户 UID |
| `PRODUCT_HUNT_TOKEN` | Product Hunt API Token（可选） |

## 运行

- **自动**：GitHub Actions 每天北京时间 09:00 执行
- **手动**：在 GitHub Actions 页面点击 "Run workflow"
- **本地调试**：
  ```bash
  pip install -r requirements.txt
  export DEEPSEEK_API_KEY=sk-xxx
  export WXPUSHER_TOKEN=AT_xxx
  export WXPUSHER_UID=UID_xxx
  python src/main.py
  ```

## 项目结构

```
├── .github/workflows/daily-brief.yml   # GitHub Actions 定时任务
├── src/
│   ├── main.py                         # 入口编排
│   ├── models.py                       # 数据模型
│   ├── summarizer.py                   # DeepSeek 摘要
│   ├── pusher.py                       # WxPusher 推送
│   └── sources/                        # 各平台抓取器
│       ├── base.py
│       ├── hacker_news.py
│       ├── reddit.py
│       ├── product_hunt.py
│       ├── huggingface.py
│       ├── github_trending.py
│       ├── zhihu.py
│       ├── sspai.py
│       └── jike.py
├── config.py                           # 全局配置
├── requirements.txt                    # Python 依赖
└── README.md
```
```

---

### 自检清单

- [x] **Spec coverage** — 所有设计文档中的数据源、组件、流程都已映射到对应任务
- [x] **No placeholders** — 所有代码块包含完整实现，无 TBD/TODO
- [x] **Type consistency** — InfoItem 在所有 fetcher 中使用一致的字段和类型
- [x] **Config alignment** — config.py 的开关与各 fetcher 的 toggles 一致
- [x] **Error handling** — 每个 fetcher 在失败时返回空列表，主流程继续执行
- [x] **YAGNI** — 没有多余功能（无 Web 界面、无数据库、无多用户）
