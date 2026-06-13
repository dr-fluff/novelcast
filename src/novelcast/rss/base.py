from abc import ABC, abstractmethod


class BaseRssReader(ABC):

    @abstractmethod
    def build_feed(self) -> str:
        pass

    @abstractmethod
    def fetch(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, xml: str) -> list[dict]:
        pass

    def run(self) -> list[dict]:
        url = self.build_feed()
        xml = self.fetch(url)
        return self.parse(xml)