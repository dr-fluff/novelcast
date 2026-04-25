# novelcast/engine/adapters/royalroad.py

from bs4 import BeautifulSoup


class RoyalRoadAdapter:

    def download_story(self, url: str):
        raise NotImplementedError("Optional fallback only")