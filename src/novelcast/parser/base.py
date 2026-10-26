# novelcast/parser/base.py

from abc import ABC, abstractmethod
from typing import NotRequired, TypedDict


class Chapter(TypedDict):
    number: int
    title: str
    content: str
    url: NotRequired[str | None]


class Story(TypedDict):
    title: str
    author: str | None
    chapters: list[Chapter]
    cover_image: NotRequired[bytes | None]
    raw_metadata: NotRequired[dict]


class BaseParser(ABC):
    @abstractmethod
    def parse(self, data: dict) -> Story:
        """
        Convert raw engine output into normalized Story structure.
        """
        pass

    def extract(self, data: dict):
        """
        Optional helper for parser implementations that need to extract content from a file.
        """
        raise NotImplementedError("extract() is not implemented for this parser")
