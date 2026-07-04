# novelcast/parser/patreon_parser.py

import re
import html
import logging
from novelcast.parser.base import BaseParser, Story

from novelcast.parser.base import BaseParser, Story

logger = logging.getLogger(__name__)


class PatreonParser(BaseParser):

    def parse(self, data: dict) -> Story:
        raw = data.get("raw", {})
        raw_chapters = raw.get("chapters", [])

        chapters = []
        number = 0

        for ch in raw_chapters:
            number += 1

            title = ch.get("title") or f"Chapter {number}"
            content = ch.get("content", "")

            html_content = self._to_html(content)

            chapters.append({
                "number": ch.get("number") or number,
                "title": title,
                "content": html_content,
            })

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters,
        }

    def _to_html(self, content: str) -> str:
        content = content.strip()

        # already HTML → preserve
        if "<p" in content or "<div" in content:
            return re.sub(r">\s+<", "><", content)

        # fallback: line-based text
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

        return "\n".join(f"<p>{p}</p>" for p in paragraphs)
    