from abc import ABC, abstractmethod


class StoryEngine(ABC):

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str, progress_callback=None) -> dict:
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
