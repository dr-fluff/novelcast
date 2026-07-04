# novelcast/parser/story_parser.py

from curses import raw

import logging

from novelcast.parser.registry import ParserRegistry

logger = logging.getLogger(__name__)

class StoryParser:

    def __init__(self, registry: ParserRegistry):
        self.registry = registry
        logger.debug("StoryParser initialized with registry: %s", registry)

    def parse(self, raw: dict) -> dict:
        logger.debug("Parsing raw story data: %s", raw)
        if raw.get("file_path"):
            parser = self.registry.get("epub")
        else:
            format_name = raw.get("format", "fanficfare")
            parser = self.registry.get(format_name)

        logger.debug("Using parser: %s", parser)
        return parser.parse(raw)