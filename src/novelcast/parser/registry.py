# novelcast/parser/registry.py

from typing import Dict
from novelcast.parser.base import BaseParser


class ParserRegistry:

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}

    def register(self, format_name: str, parser: BaseParser) -> None:
        self._parsers[format_name] = parser

    def get(self, format_name: str) -> BaseParser:
        parser = self._parsers.get(format_name)

        if not parser:
            raise ValueError(f"No parser registered for format: {format_name}")

        return parser