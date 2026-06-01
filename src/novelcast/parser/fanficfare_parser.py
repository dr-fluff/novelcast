# novelcast/parser/fanficfare_parser.py

from novelcast.parser.base import BaseParser, Story


class FanFicFareParser(BaseParser):

    def parse(self, data: dict) -> Story:
        raw = data.get("raw") if isinstance(data.get("raw"), dict) else data
        chapters = raw.get("chapters") or []
        zchapters = self._parse_zchapters(raw.get("zchapters"))

        normalized = []
        for index, ch in enumerate(chapters, start=1):
            raw_title = ch.get("title") or ""
            metadata = self._find_zchapter_metadata(raw_title, zchapters, index)
            chapter_number = metadata.get("number") or index
            title = metadata.get("title") or raw_title or f"Chapter {chapter_number}"
            url = metadata.get("url")

            normalized.append({
                "number": chapter_number,
                "title": title,
                "url": url,
                "content": ch.get("content", ""),
            })

        return {
            "title": data.get("title", raw.get("title", "Unknown")),
            "author": data.get("author", raw.get("author")),
            "chapters": normalized,
            "raw_metadata": raw,
        }

    def _parse_zchapters(self, zchapters_raw) -> dict[int, dict]:
        if not isinstance(zchapters_raw, list):
            return {}

        result: dict[int, dict] = {}
        for item in zchapters_raw:
            if (
                isinstance(item, list)
                and len(item) == 2
                and isinstance(item[0], int)
                and isinstance(item[1], dict)
            ):
                index = item[0]
                meta = item[1]
                title = meta.get("title")
                metadata_number = self._parse_chapter_number_from_title(title) if isinstance(title, str) else None
                result[index] = {
                    "number": metadata_number,
                    "title": title,
                    "url": meta.get("url"),
                }
        return result

    def _find_zchapter_metadata(self, raw_title: str, zchapters: dict[int, dict], index: int) -> dict:
        normalized_title = self._normalize_title(raw_title)
        for meta in zchapters.values():
            if self._normalize_title(meta.get("title") or "") == normalized_title:
                return meta

        raw_number = self._parse_chapter_number_from_title(raw_title)
        if raw_number is not None:
            for meta in zchapters.values():
                if meta.get("number") == raw_number:
                    return meta

        if index in zchapters:
            return zchapters[index]

        for offset in (-1, 1, -2, 2):
            candidate = index + offset
            if candidate in zchapters:
                return zchapters[candidate]

        return {}

    def _normalize_title(self, title: str) -> str:
        text = title.replace("–", "-")
        text = text.replace("—", "-")
        text = text.replace("‑", "-")
        text = text.replace("−", "-")
        text = text.replace("…", "...")
        return " ".join(text.lower().replace(".", "").split())

    def _parse_chapter_number_from_title(self, title: str) -> int | None:
        import re

        match = re.match(r"chapter\s*#?\s*(\d+)", title, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
