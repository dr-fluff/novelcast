from abc import ABC, abstractmethod

class StoryParser(ABC):

    @abstractmethod
    def parse(self, data: dict) -> dict:
        """
        Returns normalized structure:
        {
            title,
            author,
            chapters: [{number, title, content}]
        }
        """
        pass