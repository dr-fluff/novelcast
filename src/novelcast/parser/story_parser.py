class StoryParser:

    def parse(self, raw: dict) -> dict:

        if raw.get("format") == "epub":
            return self._parse_epub(raw)

        return raw

    def _parse_epub(self, raw: dict) -> dict:
        from novelcast.parser.epub_parser import EpubParser

        epub = EpubParser()
        chapters = epub.extract(raw["file_path"])

        return {
            "title": raw["title"],
            "author": raw["author"],
            "url": raw["url"],
            "chapters": chapters
        }