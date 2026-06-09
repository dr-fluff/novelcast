# novelcast/parser/registry.py

from typing import Dict

from novelcast.parser.base import BaseParser


class ParserRegistry:
    def __init__(self, parsers: Dict[str, BaseParser] | None = None):
        self._parsers = parsers or {}

    def register(self, name: str, parser: BaseParser) -> None:
        self._parsers[name] = parser

    def get(self, name: str) -> BaseParser:
        try:
            return self._parsers[name]
        except KeyError:
            raise ValueError(f"No parser registered for format: {name}") from None