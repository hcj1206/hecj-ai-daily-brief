"""Push the daily briefing to WeChat via WxPusher API."""

import logging
from datetime import datetime, timezone, timedelta

import requests

from src.models import BriefResult
from config import config

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=8))


class Pusher:
    """Send the daily brief summary as a WeChat message via WxPusher."""

    def push(self, brief: BriefResult) -> bool:
        """Push brief to WeChat. Returns True on success."""
        if not config.wxpusher_token:
            logger.error("[pusher] WxPusher token not configured")
            return False

        content = self._format_content(brief)
        payload = {
            "appToken": config.wxpusher_token,
            "content": content,
            "contentType": 1,  # 1 = plain text
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
                logger.info("[pusher] Push successful: %s", result.get("msg", ""))
                return True
            else:
                logger.error("[pusher] Push API error: %s", result)
                return False
        except Exception as e:
            logger.error("[pusher] Push failed: %s", e)
            return False

    def _format_content(self, brief: BriefResult) -> str:
        """Format the brief as a WeChat-friendly text message."""
        date_str = datetime.now(CST).strftime("%Y-%m-%d")

        if brief.error:
            return f"⚠️ AI Daily Brief · {date_str}\n\n生成失败：{brief.error}"

        return (
            f"📡 AI Daily Brief · {date_str}\n\n"
            f"{brief.summary_text}\n\n"
            f"---\n共收录 {brief.raw_count} 条资讯"
        )
