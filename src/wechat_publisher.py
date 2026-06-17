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
        import re
        lines = brief.summary_text.strip().split("\n")

        html_parts = [
            '<section style="padding: 10px 0;">',
            f'<h2 style="text-align: center; font-size: 18px; color: #333;">📡 AI 工具日报</h2>',
            f'<p style="text-align: center; color: #999; font-size: 14px; margin-bottom: 20px;">{date_str}</p>',
            f'<p style="text-align: center; color: #999; font-size: 13px; margin-bottom: 16px;">'
            f'共收录 {brief.raw_count} 条资讯</p>',
            '<hr style="border: none; border-top: 1px solid #eee;">',
            '<p style="font-size: 14px; color: #666; margin: 12px 0 16px;">👇 全部资讯</p>',
        ]

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Section headers (e.g., "### xxx")
            if line.startswith("###"):
                html_parts.append(
                    f'<h3 style="font-size: 16px; color: #07c160; '
                    f'margin: 18px 0 10px;">{line.lstrip("#").strip()}</h3>'
                )
                i += 1
                continue

            # Horizontal rule
            if line.startswith("---"):
                html_parts.append(
                    '<hr style="border: none; border-top: 1px solid #e5e5e5; '
                    'margin: 16px 0;">'
                )
                i += 1
                continue

            # Numbered item line (e.g. "1. Title [Source]")
            # The next line may be a description
            numbered_match = re.match(r'^\d+[\.\、]\s*(.+)

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
, line)
            if numbered_match:
                item_text = numbered_match.group(1)

                # Extract source tag [xxx]
                source_tag = ""
                tag_match = re.search(r'\[([^\]]+)\]', item_text)
                if tag_match:
                    source_tag = tag_match.group(1)
                    # Remove the [tag] from the text
                    item_text = re.sub(r'\s*\[([^\]]+)\]', '', item_text)

                # Look ahead for a description line (starts with "一句话简介" or is indented)
                desc_text = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    desc_match = re.match(r'(?:一句话简介[：:]\s*|简介[：:]\s*|)(.+)

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
, next_line)
                    if desc_match and not next_line.startswith("###") and not next_line.startswith("---"):
                        desc_text = desc_match.group(1)
                        i += 1  # consume the description line

                # Render item block
                item_html = (
                    f'<div style="margin: 12px 0; padding: 10px 14px; '
                    f'background: #fafafa; border-radius: 8px; '
                    f'border-left: 3px solid #07c160;">'
                    f'<div style="font-weight: 500; color: #1a1a1a; font-size: 15px; line-height: 1.6;">'
                    f'{item_text}'
                )
                if source_tag:
                    item_html += (
                        f'<span style="display: inline-block; color: #07c160; font-size: 11px; '
                        f'background: #e8f8ee; padding: 1px 8px; border-radius: 3px; '
                        f'margin-left: 6px; font-weight: 400;">{source_tag}</span>'
                    )
                item_html += '</div>'
                if desc_text:
                    item_html += (
                        f'<div style="font-size: 13px; color: #888; line-height: 1.6; '
                        f'margin-top: 4px; padding-left: 4px;">{desc_text}</div>'
                    )
                item_html += '</div>'
                html_parts.append(item_html)
                i += 1
                continue

            # Bold text (trend summary)
            if line.startswith("**") and "**" in line[2:]:
                clean = line.replace("**", "")
                html_parts.append(
                    f'<p style="font-weight: 600; color: #1a1a1a; '
                    f'font-size: 15px; margin: 14px 0 8px;">{clean}</p>'
                )
                i += 1
                continue

            # Lines with source tags
            if "[" in line and "]" in line:
                formatted = re.sub(
                    r'\[([^\]]+)\]',
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

        # Footer
        html_parts.extend([
            '<hr style="border: none; border-top: 1px solid #e5e5e5; margin: 16px 0;">',
            f'<p style="font-size: 13px; color: #999; text-align: center;">'
            f'共收录 {brief.raw_count} 条资讯</p>',
            '</section>',
        ])
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
