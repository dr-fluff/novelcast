# novelcast/parser/patreon_parser.py
import base64
import json
import logging
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub

from novelcast.parser.base import BaseParser, Story

logger = logging.getLogger(__name__)

_IMAGE_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
}

_EPUB_SKIP_MARKERS = ("cover", "nav", "toc", "titlepage", "title_page")


class PatreonParser(BaseParser):
    def parse(self, data: dict, settings: dict | None = None) -> Story:
        raw = data.get("raw", {})
        post_records = raw.get("post_records", [])
        settings = settings or {}

        chapters = []
        for record in post_records:
            chapters.extend(self._parse_post_record(record, settings))

        chapters = self._normalize_chapters(chapters)

        for ch in chapters:
            ch["content"] = self._to_html(ch.get("content", ""))

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters,
        }

    # ── per-post resolution ──────────────────────────────────────────

    def _parse_post_record(self, record: dict, settings: dict) -> list[dict]:
        content_source = settings.get("content_source") or "file"
        filename_pattern = settings.get("filename_pattern")

        files = record.get("files", [])
        doc_files = [f for f in files if f.get("type") in ("pdf", "epub")]
        post_title = record.get("title", "Untitled")

        use_files = bool(doc_files) and content_source != "text"

        if use_files:
            chapters = []
            for f in doc_files:
                content = (
                    self._extract_epub_text(f["path"]) if f["type"] == "epub" else self._extract_pdf_text(f["path"])
                )
                if not content.strip():
                    continue
                num, title = self._extract_number_title_from_filename(f["filename"], filename_pattern)
                chapters.append(
                    {
                        "number": num if num is not None else self._extract_chapter_number_from_title(post_title),
                        "title": title or post_title,
                        "content": content,
                    }
                )

            if not chapters:
                # Files existed but all failed to parse — fall back to post text
                # so nothing is silently lost.
                return self._text_only_chapter(record, post_title, embed_images=True)

            # Leftover post text becomes an author note attached to every
            # chapter this post produced. Images are intentionally NOT embedded
            # here, per your rule 4 — only text-only chapters get images.
            note_html = self._post_content_to_html(record, embed_images=False)
            if note_html.strip():
                wrapped = self._wrap_author_note(note_html)
                for ch in chapters:
                    ch["content"] = ch["content"] + "\n" + wrapped

            return chapters

        return self._text_only_chapter(record, post_title, embed_images=True)

    def _text_only_chapter(self, record: dict, post_title: str, embed_images: bool) -> list[dict]:
        content_html = self._post_content_to_html(record, embed_images=embed_images)

        image_files = [f for f in record.get("files", []) if f.get("type") == "image"]
        if embed_images and image_files:
            prefix = "\n".join(self._file_to_img_tag(f) for f in image_files)
            content_html = f"{prefix}\n{content_html}" if content_html.strip() else prefix

        if not content_html.strip():
            return []

        num = self._extract_chapter_number_from_title(post_title)
        return [{"number": num, "title": post_title, "content": content_html}]

    # ── content format conversion ────────────────────────────────────

    def _post_content_to_html(self, record: dict, embed_images: bool) -> str:
        content_format = record.get("content_format", "html")
        raw_content = record.get("raw_content", "")
        if not raw_content:
            return ""

        if content_format == "tiptap_json":
            try:
                doc = json.loads(raw_content)
            except Exception as e:
                logger.warning("Failed to parse tiptap content: %s", e)
                return ""
            inline_images = record.get("inline_images", {}) if embed_images else {}
            return self._tiptap_to_html(doc, inline_images, embed_images)

        return raw_content  # already HTML — keep raw, per original "DO NOT STRIP IT" note

    def _tiptap_to_html(self, node, inline_images: dict | None = None, embed_images: bool = True) -> str:
        inline_images = inline_images or {}

        if isinstance(node, dict):
            ntype = node.get("type")

            if ntype == "text":
                text = node.get("text", "")
                for mark in node.get("marks", []) or []:
                    mtype = mark.get("type")
                    if mtype == "bold":
                        text = f"<strong>{text}</strong>"
                    elif mtype == "italic":
                        text = f"<em>{text}</em>"
                    elif mtype == "strike":
                        text = f"<s>{text}</s>"
                    elif mtype == "link":
                        href = (mark.get("attrs") or {}).get("href", "#")
                        text = f'<a href="{href}">{text}</a>'
                return text

            if ntype == "image":
                if not embed_images:
                    return ""
                src = (node.get("attrs") or {}).get("src")
                local_path = inline_images.get(src)
                if local_path and os.path.exists(local_path):
                    mime = self._guess_mime(local_path)
                    with open(local_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("ascii")
                    return f'<img src="data:{mime};base64,{encoded}" alt="" />'
                if src:
                    return f'<img src="{src}" alt="" />'
                return ""

            inner = "".join(self._tiptap_to_html(c, inline_images, embed_images) for c in node.get("content", []) or [])

            if ntype == "paragraph":
                return f"<p>{inner}</p>" if inner else "<p></p>"
            if ntype == "heading":
                level = min(max(int((node.get("attrs") or {}).get("level", 3)), 1), 6)
                return f"<h{level}>{inner}</h{level}>"
            if ntype == "bulletList":
                return f"<ul>{inner}</ul>"
            if ntype == "orderedList":
                return f"<ol>{inner}</ol>"
            if ntype == "listItem":
                return f"<li>{inner}</li>"
            if ntype == "blockquote":
                return f"<blockquote>{inner}</blockquote>"
            if ntype == "horizontalRule":
                return "<hr/>"
            if ntype == "hardBreak":
                return "<br/>"

            return inner

        if isinstance(node, list):
            return "".join(self._tiptap_to_html(n, inline_images, embed_images) for n in node)

        return ""

    def _file_to_img_tag(self, file_ref: dict) -> str:
        path = file_ref.get("path")
        filename = file_ref.get("filename", "")
        if not path or not os.path.exists(path):
            return ""
        mime = self._guess_mime(path)
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f'<img src="data:{mime};base64,{encoded}" alt="{filename}" />'

    def _guess_mime(self, path: str) -> str:
        ext = Path(path).suffix.lower().lstrip(".")
        return _IMAGE_MIME.get(ext, "application/octet-stream")

    def _wrap_author_note(self, html_content: str) -> str:
        # Matches the structure the existing reader CSS already hides via
        # hide_author_notes — no new schema/toggle needed.
        return (
            '<div class="portlet solid author-note-portlet">'
            '<div class="portlet-body author-note">'
            f"{html_content}"
            "</div></div>"
        )

    # ── PDF / EPUB extraction (one file = one chapter, no internal splitting) ──

    def _extract_pdf_text(self, file_path: str) -> str:
        if not file_path or not os.path.exists(file_path):
            return ""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                pdf = PyPDF2.PdfReader(f)
                paragraphs = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    for line in text.split("\n"):
                        line = line.strip()
                        if line:
                            paragraphs.append(f"<p>{self._escape(line)}</p>")
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error("Failed to parse PDF %s: %s", file_path, e)
            return ""

    def _extract_epub_text(self, file_path: str) -> str:
        if not file_path or not os.path.exists(file_path):
            return ""
        try:
            book = epub.read_epub(file_path)
            parts = []
            for item in book.get_items():
                if item.get_type() != ITEM_DOCUMENT:
                    continue
                name = (item.get_name() or "").lower()
                if any(marker in name for marker in _EPUB_SKIP_MARKERS):
                    continue
                soup = BeautifulSoup(item.get_content(), "html.parser")
                body = soup.find("body")
                inner_html = "".join(str(c) for c in body.contents) if body else str(soup)
                parts.append(inner_html)
            return "\n".join(parts)
        except Exception as e:
            logger.error("Failed to parse EPUB %s: %s", file_path, e)
            return ""

    def _escape(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ── filename → chapter number/title ──────────────────────────────

    def _extract_number_title_from_filename(self, filename: str, pattern: str | None) -> tuple[int | None, str]:
        stem = Path(filename).stem

        if pattern:
            try:
                compiled = re.compile(pattern)
                m = compiled.search(stem)
                if m:
                    gd = m.groupdict()
                    num = None
                    if gd.get("number"):
                        digits = re.sub(r"[^\d]", "", gd["number"])
                        if digits:
                            num = int(digits)
                    title = (gd.get("title") or "").strip(" -_:") or None
                    if num is not None or title:
                        return num, title or self._clean_filename_title(stem)
            except re.error as e:
                logger.warning("Invalid filename_pattern %r: %s", pattern, e)

        # Generic fallback — first standalone number in the filename.
        # NOTE: unreliable when the filename has a leading series/story number
        # before the actual chapter number (e.g. "The 108 Chapter 35 ..." would
        # match "108", not "35"). Set filename_pattern per-story to fix.
        num = None
        m = re.search(r"(\d+)", stem)
        if m:
            try:
                num = int(m.group(1))
            except ValueError:
                num = None
        return num, self._clean_filename_title(stem)

    def _clean_filename_title(self, stem: str) -> str:
        cleaned = re.sub(r"\(.*?\)", "", stem)
        cleaned = cleaned.replace("_", " ").strip(" -_:")
        return cleaned or stem

    def _extract_chapter_number_from_title(self, title: str) -> int:
        match = re.search(r"\b(\d+)\b", title)
        return int(match.group(1)) if match else 1

    def _normalize_chapters(self, chapters: list[dict]) -> list[dict]:
        chapters.sort(key=lambda x: x.get("number", 0))
        for idx, ch in enumerate(chapters, 1):
            ch["number"] = idx
        return chapters

    def _to_html(self, content: str) -> str:
        content = (content or "").strip()
        if not content:
            return content
        if "<p" in content or "<div" in content or "<h" in content:
            return re.sub(r">\s+<", "><", content)
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        return "\n".join(f"<p>{p}</p>" for p in paragraphs)
