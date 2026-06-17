"""Publish the daily brief as a draft article to WeChat Official Account."""

import logging
import struct
import zlib
import io
import hashlib
from datetime import datetime, timezone, timedelta

import requests

from src.models import BriefResult
from config import config

logger = logging.getLogger(__name__)
CST = timezone(timedelta(hours=8))

WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"


class WeChatPublisher:
    """Create a draft article in the WeChat Official Account draft box."""

    def __init__(self):
        self.access_token = ""

    def publish(self, brief: BriefResult) -> bool:
        """Main entry point: create a draft from the brief."""
        if not config.wechat_app_id or not config.wechat_app_secret:
            logger.error("[wechat] WECHAT_APP_ID or WECHAT_APP_SECRET not configured")
            return False

        # 1. Get access token
        self.access_token = self._get_access_token()
        if not self.access_token:
            return False

        # 2. Generate a cover image and upload as permanent material
        thumb_media_id = self._upload_cover()
        if not thumb_media_id:
            logger.warning("[wechat] Cover upload failed, proceeding without custom cover")
            # WeChat may auto-select a cover if we don't provide one,
            # but the API requires thumb_media_id. We'll use a placeholder.

        # 3. Upload any images used in the article content
        # (For now the article is text-only, so this is a no-op.
        #  If we add images later, upload them via uploadimg here.)

        # 4. Create the draft article
        draft_media_id = self._create_draft(brief, thumb_media_id)
        if draft_media_id:
            logger.info("[wechat] Draft created successfully! media_id=%s", draft_media_id)
            logger.info("[wechat] Go to mp.weixin.qq.com → 草稿箱 to review and publish.")
            return True
        return False

    def _get_access_token(self) -> str:
        """Obtain an access_token from WeChat API."""
        url = f"{WECHAT_API_BASE}/token"
        params = {
            "grant_type": "client_credential",
            "appid": config.wechat_app_id,
            "secret": config.wechat_app_secret,
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "access_token" in data:
                logger.info("[wechat] Access token obtained")
                return data["access_token"]
            else:
                logger.error("[wechat] Token error: %s", data)
                return ""
        except Exception as e:
            logger.error("[wechat] Failed to get access_token: %s", e)
            return ""

    def _upload_cover(self) -> str:
        """Generate a simple cover image and upload as permanent material.

        Returns thumb_media_id, or empty string on failure.
        """
        date_str = datetime.now(CST).strftime("%Y-%m-%d")

        # Generate a simple colored PNG
        # Use date hash to pick a color so it changes daily
        color_hash = int(hashlib.md5(date_str.encode()).hexdigest()[:6], 16)
        r = (color_hash >> 16) & 0xFF
        g = (color_hash >> 8) & 0xFF
        b = color_hash & 0xFF

        png_data = self._make_png(400, 200, r, g, b)

        url = f"{WECHAT_API_BASE}/material/add_material"
        try:
            files = {
                "media": (f"cover_{date_str}.png", png_data, "image/png"),
            }
            params = {"access_token": self.access_token, "type": "image"}
            r = requests.post(url, params=params, files=files, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "media_id" in data:
                logger.info("[wechat] Cover uploaded: %s", data["media_id"])
                return data["media_id"]
            else:
                logger.error("[wechat] Cover upload error: %s", data)
                return ""
        except Exception as e:
            logger.error("[wechat] Cover upload failed: %s", e)
            return ""

    def _create_draft(self, brief: BriefResult, thumb_media_id: str) -> str:
        """Create a draft article in the WeChat draft box.

        Returns media_id of the draft, or empty string on failure.
        """
        date_str = datetime.now(CST).strftime("%Y-%m-%d")
        title = f"📡 AI Daily Brief · {date_str}"
        digest = f"共收录 {brief.raw_count} 条资讯，AI 工具行业每日速览"

        if brief.error:
            content = f"<p>今日简报生成失败：{brief.error}</p>"
        else:
            # Convert the summary text to HTML
            content = self._format_article_html(brief, date_str)

        # Limit title to 64 chars (WeChat limit)
        title = title[:64]

        article = {
            "title": title,
            "author": config.wechat_article_author,
            "digest": digest[:120],  # WeChat limit: 120 chars
            "content": content,
            "content_source_url": "",
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }

        url = f"{WECHAT_API_BASE}/draft/add"
        params = {"access_token": self.access_token}
        payload = {"articles": [article]}

        try:
            r = requests.post(url, params=params, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "media_id" in data:
                logger.info("[wechat] Draft added: %s", data["media_id"])
                return data["media_id"]
            else:
                logger.error("[wechat] Draft error: %s", data)
                return ""
        except Exception as e:
            logger.error("[wechat] Draft creation failed: %s", e)
            return ""

    def _format_article_html(self, brief: BriefResult, date_str: str) -> str:
        """Convert the brief summary into WeChat-compatible HTML."""
        lines = brief.summary_text.strip().split("\n")

        html_parts = [
            '<section style="padding: 10px 0;">',
            f'<h2 style="text-align: center; font-size: 18px; color: #333;">📡 AI 工具日报</h2>',
            f'<p style="text-align: center; color: #999; font-size: 14px; margin-bottom: 20px;">{date_str}</p>',
            '<hr style="border: none; border-top: 1px solid #eee;">',
        ]

        for line in lines:
            line = line.strip()
            if not line:
                html_parts.append("<br>")
                continue

            # Section headers (e.g., "### xxx")
            if line.startswith("###"):
                html_parts.append(
                    f'<h3 style="font-size: 16px; color: #07c160; '
                    f'margin: 15px 0 10px;">{line.lstrip("#").strip()}</h3>'
                )
            # Horizontal rule
            elif line.startswith("---"):
                html_parts.append(
                    '<hr style="border: none; border-top: 1px solid #ddd; '
                    'margin: 15px 0;">'
                )
            # Bold trend summary
            elif line.startswith("**") and line.endswith("**"):
                html_parts.append(
                    f'<p style="font-weight: bold; color: #333; '
                    f'font-size: 15px; margin: 10px 0;">{line.strip("*")}</p>'
                )
            # Source tags like [Hacker News]
            elif "[" in line and "]" in line:
                # Wrap source tags in colored spans
                formatted = line
                import re
                formatted = re.sub(
                    r'\[([^\]]+)\]',
                    r'<span style="color: #07c160; font-size: 12px;'
                    r' background: #f0faf0; padding: 1px 6px;'
                    r' border-radius: 3px;">[\1]</span>',
                    formatted,
                )
                html_parts.append(
                    f'<p style="font-size: 15px; line-height: 1.8; '
                    f'margin: 6px 0;">{formatted}</p>'
                )
            else:
                html_parts.append(
                    f'<p style="font-size: 15px; line-height: 1.8; '
                    f'margin: 6px 0;">{line}</p>'
                )

        html_parts.append("</section>")
        return "\n".join(html_parts)

    @staticmethod
    def _make_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
        """Create a minimal solid-color PNG image using only built-in modules.

        This generates a valid PNG with IHDR, IDAT, and IEND chunks.
        The image is a solid rectangle with the given RGB color.
        """
        def _chunk(chunk_type: bytes, data: bytes) -> bytes:
            c = chunk_type + data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(data)) + c + crc

        # PNG signature
        sig = b'\x89PNG\r\n\x1a\n'

        # IHDR: width, height, bit_depth=8, color_type=2 (RGB),
        #       compression=0, filter=0, interlace=0
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        ihdr = _chunk(b'IHDR', ihdr_data)

        # IDAT: raw pixel data (filter byte 0 + RGB pixels per row)
        raw = b''
        row = b'\x00' + bytes([r, g, b]) * width
        for _ in range(height):
            raw += row
        idat = _chunk(b'IDAT', zlib.compress(raw))

        iend = _chunk(b'IEND', b'')

        return sig + ihdr + idat + iend
