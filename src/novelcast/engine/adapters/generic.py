# novelcast/engine/adapters/generic.py

from bs4 import BeautifulSoup
from urllib.request import urlopen
from .base import BaseAdapter


class GenericAdapter(BaseAdapter):

    def __init__(self, config=None):
        super().__init__(config)
    # -------------------------
    # metadata extraction
    # -------------------------
    def get_metadata(self, html: str):
        soup = BeautifulSoup(html, "html.parser")

        title = (
            soup.find("h1")
            or soup.find("title")
        )

        title_text = title.get_text(strip=True) if title else "Unknown Title"

        # try to guess author
        author = "Unknown"
        text = soup.get_text(" ", strip=True)

        # weak heuristic patterns
        if " by " in text.lower():
            try:
                author = text.lower().split(" by ")[-1].split(" ")[0]
            except Exception:
                pass

        return {
            "title": title_text,
            "author": author
        }

    # -------------------------
    # chapter list extraction
    # -------------------------
    def get_chapter_list(self, url: str):
        """
        Heuristic:
        - find all <a> tags
        - filter likely chapter links
        """

        html = urlopen(url).read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        chapters = []
        links = soup.find_all("a", href=True)

        chapter_keywords = [
            "chapter", "chap", "c", "ep", "episode"
        ]

        index = 1

        for a in links:
            text = a.get_text(strip=True).lower()
            href = a["href"]

            if not text:
                continue

            if any(k in text for k in chapter_keywords):
                chapters.append((index, a.get_text(strip=True), href))
                index += 1

        # fallback: if nothing found, treat page as single chapter
        if not chapters:
            chapters.append((1, "Chapter 1", url))

        return chapters

    # -------------------------
    # chapter content extraction
    # -------------------------
    def get_chapter_content(self, html: str):
        soup = BeautifulSoup(html, "html.parser")

        # remove noise
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()

        # try common containers first
        selectors = [
            "article",
            ".chapter-content",
            ".entry-content",
            "#content",
            "main"
        ]

        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                return str(node)

        # fallback: largest text block
        paragraphs = soup.find_all("p")
        if paragraphs:
            return "".join(str(p) for p in paragraphs)

        # last fallback: whole body
        body = soup.find("body")
        return str(body) if body else str(soup)