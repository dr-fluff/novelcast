from abc import ABC, abstractmethod


class RssFeed(ABC):

    def __init__(self):
        self.base_link = None

    @abstractmethod
    def create_link(self) -> str:
        """Return full RSS URL"""
        pass

    @abstractmethod
    def read_rss(self, url: str):
        """Fetch RSS XML"""
        pass

    @abstractmethod
    def parse_rss(self, raw_feed):
        """Convert RSS → structured items"""
        pass