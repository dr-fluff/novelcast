# novelcast/parser/fanficfare_parser.py

from novelcast.parser.base import BaseParser, Story


class FanFicFareParser(BaseParser):

    def parse(self, data: dict) -> Story:
        raw = data.get("raw", {})
        chapters = raw.get("chapters", [])

        normalized = [
            {
                "number": i,
                "title": ch.get("title", f"Chapter {i}"),
                "content": ch.get("content", "")
            }
            for i, ch in enumerate(chapters, start=1)
        ]

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": normalized
        }