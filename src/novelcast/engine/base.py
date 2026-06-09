# novelcast/engine/base.py
from abc import ABC, abstractmethod


class StoryEngine(ABC):

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        """
        Must return:
        {
            title,
            author,
            url,
            chapters | None,
            file_path | None
        }
        """
        pass

    def check_updates(self, url: str) -> dict:
        raise NotImplementedError(f"{self.__class__.__name__} does not support update checks")

    