
import re

from novelcast.parser.base import BaseParser, Story


class FanFicFareParser(BaseParser):
    def parse(self, data: dict) -> Story:
        raw = data.get("raw") if isinstance(data.get("raw"), dict) else data
        chapters = raw.get("chapters") or []
        zchapters = self._parse_zchapters(raw.get("zchapters"))

        normalized = []
        for index, ch in enumerate(chapters, start=1):
            raw_title = ch.get("title") or ""
            metadata = self._find_zchapter_metadata(raw_title, zchapters)

            # Keep NovelCast's internal index separate from source numbering.
            title = metadata.get("title") or raw_title or f"Chapter {index}"
            url = metadata.get("url")

            normalized.append(
                {
                    "number": index,
                    "title": title,
                    "url": url,
                    "content": ch.get("content", ""),
                }
            )

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
                index, meta = item
                title = meta.get("title")
                result[index] = {
                    "number": (
                        self._parse_chapter_number_from_title(title)
                        if isinstance(title, str)
                        else None
                    ),
                    "title": title,
                    "url": meta.get("url"),
                }
        return result

    def _find_zchapter_metadata(
        self, raw_title: str, zchapters: dict[int, dict]
    ) -> dict:
        normalized_title = self._normalize_title(raw_title)

        # Exact normalized title matches are the strongest evidence.
        exact_matches = [
            meta
            for meta in zchapters.values()
            if normalized_title
            and self._normalize_title(meta.get("title") or "") == normalized_title
        ]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            return {}

        # A number is safe only when it uniquely identifies one metadata entry.
        raw_number = self._parse_chapter_number_from_title(raw_title)
        if raw_number is not None:
            number_matches = [
                meta
                for meta in zchapters.values()
                if meta.get("number") == raw_number
            ]
            if len(number_matches) == 1:
                return number_matches[0]

        # Never guess from an index or a neighboring chapter.
        return {}

    def _normalize_title(self, title: str) -> str:
        text = title
        for char in ("–", "—", "‑", "−"):
            text = text.replace(char, "-")
        text = text.replace("…", "...")
        return " ".join(text.lower().replace(".", "").split())

    def _parse_chapter_number_from_title(self, title: str) -> int | None:
        # Accept titles such as "Chapter 509" and
        # "The Path of Ascension Chapter 509".
        match = re.search(r"\bchapter\s*#?\s*(\d+)\b", title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
