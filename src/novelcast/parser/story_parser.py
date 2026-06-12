# novelcast/parser/story_parser.py

from novelcast.parser.registry import ParserRegistry


class StoryParser:

    def __init__(self, registry: ParserRegistry):
        self.registry = registry

    def parse(self, raw: dict) -> dict:
        if raw.get("file_path"):
            parser = self.registry.get("epub")
        else:
            format_name = raw.get("format", "fanficfare")
            parser = self.registry.get(format_name)

        return parser.parse(raw)