# novelcast/parser/base.py

from abc import ABC, abstractmethod
from typing import TypedDict, List, Optional


class Chapter(TypedDict):
    number: int
    title: str
    content: str


class Story(TypedDict):
    title: str
    author: Optional[str]
    chapters: List[Chapter]


class BaseParser(ABC):

    @abstractmethod
    def parse(self, data: dict) -> Story:
        """
        Convert raw engine output into normalized Story structure.
        """
        pass
    
    @abstractmethod
    def extract(self, data: dict) -> Story:
        pass