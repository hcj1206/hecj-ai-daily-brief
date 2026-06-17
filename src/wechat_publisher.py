"""Publish the daily brief as a draft article to WeChat Official Account."""

import logging
import struct
import zlib
import re
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
            logger.error("WECHAT_APP_ID or WECHAT_APP_SECRET not configured")
            return False

        self.access_token = self._get_access_token()
        if not self.access_token:
            return False

        thumb_media_id = self._upload_cover()

        draft_media_id = self._create_draft(brief, thumb_media_id)
        if draft_media_id:
            logger.info("Draft created! media_id=%s Go to mp.weixin.qq.com -> draft box to publish.", draft_media_id)
            return True
        return False

    def _get_access_token(self) -> str:
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
                logger.info("Access token obtained")
                return data["access_token"]
            else:
                logger.error("Token error: %s", data)
                return ""
        except Exception as e:
            logger.error("Failed to get access_token: %s", e)
            return ""

    def _upload_cover(self) -> str:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")
        color_hash = int(hashlib.md5(date_str.encode()).hexdigest()[:6], 16)
        r = (color_hash >> 16) & 0xFF
        g = (color_hash >> 8) & 0xFF
        b = color_hash & 0xFF
        png_data = self._make_png(400, 200, r, g, b)

        url = f"{WECHAT_API_BASE}/material/add_material"
        try:
            files = {"media": (f"cover_{date_str}.png", png_data, "image/png")}
            params = {"access_token": self.access_token, "type": "image"}
            r = requests.post(url, params=params, files=files, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "media_id" in data:
                logger.info("Cover uploaded: %s", data["media_id"])
                return data["media_id"]
            else:
                logger.error("Cover upload error: %s", data)
                return ""
        except Exception as e:
            logger.error("Cover upload failed: %s", e)
            return ""

    def _create_draft(self, brief: BriefResult, thumb_media_id: str) -> str:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")
        title = f"📡 AI Daily Brief \u00b7 {date_str}"[:64]
        digest = f"\u5171\u6536\u5f55 {brief.raw_count} \u6761\u8d44\u8baf\uff0cAI \u5de5\u5177\u884c\u4e1a\u6bcf\u65e5\u901f\u89c8"[:120]

        if brief.error:
            content = f"<p>\u4eca\u65e5\u7b80\u62a5\u751f\u6210\u5931\u8d25\uff1a{brief.error}</p>"
        else:
            content = self._format_article_html(brief, date_str)

        article = {
            "title": title,
            "author": config.wechat_article_author,
            "digest": digest,
            "content": content,
            "content_source_url": "",
            "thumb_media_id": thumb_media_id or "",
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
                logger.info("Draft added: %s", data["media_id"])
                return data["media_id"]
            else:
                logger.error("Draft error: %s", data)
                return ""
        except Exception as e:
            logger.error("Draft creation failed: %s", e)
            return ""

    def _format_article_html(self, brief: BriefResult, date_str: str) -> str:
        """Convert the brief summary into WeChat-compatible HTML."""
        lines = brief.summary_text.strip().split("\n")

        html_parts = [
            '<section style="padding: 10px 0;">',
            '<h2 style="text-align: center; font-size: 18px; color: #333;">\U0001f4e1 AI \u5de5\u5177\u65e5\u62a5</h2>',
            f'<p style="text-align: center; color: #999; font-size: 14px; margin-bottom: 20px;">{date_str}</p>',
            f'<p style="text-align: center; color: #999; font-size: 13px; margin-bottom: 16px;">'
            f'\u5171\u6536\u5f55 {brief.raw_count} \u6761\u8d44\u8baf</p>',
            '<hr style="border: none; border-top: 1px solid #eee;">',
        ]

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Section headers
            if line.startswith("###"):
                text = line.lstrip("#").strip()
                html_parts.append(
                    f'<h3 style="font-size: 16px; color: #07c160; '
                    f'margin: 18px 0 10px;">{text}</h3>'
                )
                i += 1
                continue

            # Horizontal rule
            if line.startswith("---"):
                html_parts.append(
                    '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">'
                )
                i += 1
                continue

            # Numbered item line: "1. Title [Source]"
            # Followed optionally by a description line
            m = re.match(r"^\d+[\.\u3001]\s*(.+)$", line)
            if m:
                item_text = m.group(1)

                # Extract source tag
                source_tag = ""
                tag_m = re.search(r"\[([^\]]+)\]", item_text)
                if tag_m:
                    source_tag = tag_m.group(1)
                    item_text = re.sub(r"\s*\[([^\]]+)\]", "", item_text)

                # Peek at next line for description
                desc_text = ""
                if i + 1 < len(lines):
                    nx = lines[i + 1].strip()
                    is_desc = nx.startswith("\u4e00\u53e5\u8bdd\u7b80\u4ecb")  # 一句话简介
                    is_desc = is_desc or nx.startswith("\u7b80\u4ecb")  # 简介
                    if is_desc and not nx.startswith("###") and not nx.startswith("---"):
                        dm = re.search(r"[:：]\s*(.+)", nx)
                        if dm:
                            desc_text = dm.group(1)
                        else:
                            desc_text = nx
                        i += 1

                block = (
                    '<div style="margin: 12px 0; padding: 10px 14px; '
                    'background: #fafafa; border-radius: 8px; '
                    'border-left: 3px solid #07c160;">'
                    '<div style="font-weight: 500; color: #1a1a1a; font-size: 15px; line-height: 1.6;">'
                    f'{item_text}'
                )
                if source_tag:
                    block += (
                        f'<span style="display: inline-block; color: #07c160; font-size: 11px; '
                        f'background: #e8f8ee; padding: 1px 8px; border-radius: 3px; '
                        f'margin-left: 6px; font-weight: 400;">{source_tag}</span>'
                    )
                block += "</div>"
                if desc_text:
                    block += (
                        f'<div style="font-size: 13px; color: #888; line-height: 1.6; '
                        f'margin-top: 4px; padding-left: 4px;">{desc_text}</div>'
                    )
                block += "</div>"
                html_parts.append(block)
                i += 1
                continue

            # Bold trend summary
            if line.startswith("**") and "**" in line[2:]:
                clean = line.replace("**", "")
                html_parts.append(
                    f'<p style="font-weight: 600; color: #1a1a1a; '
                    f'font-size: 15px; margin: 14px 0 8px;">{clean}</p>'
                )
                i += 1
                continue

            # Lines with source tags (not numbered)
            if "[" in line and "]" in line:
                formatted = re.sub(
                    r"\[([^\]]+)\]",
                    r'<span style="color: #07c160; font-size: 12px;'
                    r' background: #f0faf0; padding: 1px 6px;'
                    r' border-radius: 3px;">[\1]</span>',
                    line,
                )
                html_parts.append(
                    f'<p style="font-size: 15px; line-height: 1.8; '
                    f'margin: 6px 0;">{formatted}</p>'
                )
                i += 1
                continue

            # Regular paragraph
            html_parts.append(
                f'<p style="font-size: 15px; line-height: 1.8; '
                f'margin: 6px 0;">{line}</p>'
            )
            i += 1

        html_parts.extend([
            '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">',
            f'<p style="font-size: 13px; color: #999; text-align: center;">'
            f'\u5171\u6536\u5f55 {brief.raw_count} \u6761\u8d44\u8baf</p>',
            "</section>",
        ])
        return "\n".join(html_parts)

    @staticmethod
    def _make_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
        """Create a minimal solid-color PNG image using only built-in modules."""
        def _chunk(chunk_type: bytes, data: bytes) -> bytes:
            c = chunk_type + data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(data)) + c + crc

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        ihdr = _chunk(b"IHDR", ihdr_data)
        raw = b""
        row = b"\x00" + bytes([r, g, b]) * width
        for _ in range(height):
            raw += row
        idat = _chunk(b"IDAT", zlib.compress(raw))
        iend = _chunk(b"IEND", b"")
        return sig + ihdr + idat + iend
