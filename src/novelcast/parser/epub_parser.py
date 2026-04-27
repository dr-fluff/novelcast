# novelcast/parser/epub_parser.py

from novelcast.parser.base import BaseParser, Story
from pathlib import Path

class EpubParser(BaseParser):

    def parse(self, data: dict) -> dict:
        epub_path = Path(data["file_path"])

        chapters = self.extract(epub_path)

        return {
            "title": data["title"],
            "author": data["author"],
            "chapters": chapters
        }

    def extract(self, epub_path: Path):
        # later ebooklib logic
        return []