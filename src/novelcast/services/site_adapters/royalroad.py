import re
from typing import Optional


class RoyalRoadAdapter:
    name = "royalroad"

    _FICTION_RE = re.compile(r"https?://.*royalroad\.com/fiction/(\d+)")
    _AUTHOR_RE = re.compile(r"https?://.*royalroad\.com/profile/(\d+)")

    def match_fiction_url(self, raw: str) -> Optional[str]:
        m = self._FICTION_RE.match(raw)
        return m.group(1) if m else None

    def match_author_url(self, raw: str) -> Optional[str]:
        m = self._AUTHOR_RE.match(raw)
        return m.group(1) if m else None

    def fiction_url(self, identifier: str) -> str:
        return f"https://www.royalroad.com/fiction/{identifier}"

    def author_url(self, identifier: str) -> str:
        return f"https://www.royalroad.com/profile/{identifier}/fictions"

    def fiction_search_url(self, query_text: str) -> str:
        return f"https://www.royalroad.com/fictions/search?title={query_text}"

    def author_search_url(self, query_text: str) -> str:
        return f"https://www.royalroad.com/fictions/search?author={query_text}"