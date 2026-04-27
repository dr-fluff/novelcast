# novelcast/parser/story_parser.py

from novelcast.parser.registry import ParserRegistry


class StoryParser:

    def __init__(self, registry: ParserRegistry):
        self.registry = registry

    def parse(self, raw: dict) -> dict:
        format_name = raw.get("format", "epub")

        parser = self.registry.get(format_name)
        story = parser.parse(raw)

        return story