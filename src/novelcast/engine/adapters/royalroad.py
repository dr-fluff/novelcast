# novelcast/engine/adapters/royalroad.py

from bs4 import BeautifulSoup
from urllib.request import urlopen
from .base import BaseAdapter

class RoyalRoadAdapter(BaseAdapter):

    def get_metadata(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("h1").text.strip()

        author_tag = soup.select_one(".author-name")
        author = author_tag.text.strip() if author_tag else "Unknown"

        return {"title": title, "author": author}

    def get_chapter_list(self, url: str):
        soup = BeautifulSoup(urlopen(url).read(), "html.parser")

        chapters = []
        links = soup.select("a.chapter-link")

        for i, a in enumerate(links, 1):
            chapters.append((i, a.text.strip(), a["href"]))

        return chapters

    def get_chapter_content(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        content = soup.select_one(".chapter-content")
        return str(content) if content else ""