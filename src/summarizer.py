"""AI summarizer using DeepSeek API to generate daily briefing."""

import logging

import requests

from src.models import InfoItem, BriefResult
from config import config

logger = logging.getLogger(__name__)


class Summarizer:
    """Send fetched items to DeepSeek and generate a concise daily brief."""

    def summarize(self, items: list[InfoItem]) -> BriefResult:
        """Generate a structured brief from a list of InfoItems."""
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
        logger.info("[summarizer] Generated brief of %d chars from %d items",
                     len(result.summary_text), len(items))
        return result

    def _build_prompt(self, items: list[InfoItem]) -> str:
        """Build a structured prompt for the AI model."""
        lines = [
            "你是一个 AI 工具资讯编辑。请根据以下当日收集的 AI 工具资讯，",
            "生成一份详细的每日简报。要求：",
            "1. **必须包含下面列表中的每一条资讯，共 %d 条，一条都不能少**" % len(items),
            "2. 每条资讯的格式为：",
            "   标题内容 [来源]",
            "   一句话简介：xxx",
            "3. 按推荐度从高到低排列",
            "4. 最后用 --- 分隔，给出一个趋势总结（2句话）",
            "5. 如果条目超过30条，不要省略，全部列出",
            "",
            "格式示例：",
            "1. Wolfram 发布 Mathematica 15 [Hacker News]",
            "   一句话简介：新版 Mathematica 集成了 AI 编程助手",
            "",
            "今日资讯列表（共 %d 条，请全部输出）：" % len(items),
        ]
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. [{item.source}] {item.title} — {item.description}"
            )
        return "\n".join(lines)

    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API and return the response text."""
        if not config.deepseek_api_key:
            logger.error("[summarizer] No DeepSeek API key configured")
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
            content = data["choices"][0]["message"]["content"]
            logger.info("[summarizer] DeepSeek API call successful (%d tokens)",
                         data.get("usage", {}).get("total_tokens", 0))
            return content
        except Exception as e:
            logger.error("[summarizer] DeepSeek API call failed: %s", e)
            return ""
