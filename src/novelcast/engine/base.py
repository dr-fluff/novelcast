# novelcast/engine/base.py
from abc import ABC, abstractmethod

class StoryEngine(ABC):

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str) -> dict:
        """
        Returns RAW data:
        - title
        - author
        - optional epub_path OR raw chapters
        """
        pass