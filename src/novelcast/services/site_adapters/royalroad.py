import re

from .base import SiteQueryMatch


class RoyalRoadAdapter:
    name = "royalroad"
    query_prefixes = ("royalroad", "rr")

    _FICTION_RE = re.compile(r"https?://.*royalroad\.com/fiction/(\d+)")
    _AUTHOR_RE = re.compile(r"https?://.*royalroad\.com/profile/(\d+)")

    def match_fiction_url(self, raw: str) -> str | None:
        m = self._FICTION_RE.match(raw)
        return m.group(1) if m else None

    def match_author_url(self, raw: str) -> str | None:
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

    def parse_identifier(self, remainder: str) -> SiteQueryMatch:
        # Accepts either order: "{id}/{name}" or "{name}/{id}" — whichever
        # segment is numeric wins as the id.
        for part in (p.strip() for p in remainder.split("/")):
            if part.isdigit():
                return SiteQueryMatch(target="fiction", lookup_type="id", identifier=part)
        return SiteQueryMatch(target="fiction", lookup_type="text", identifier=remainder.strip())

    def match_bare(self, raw: str) -> SiteQueryMatch | None:
        if raw.isdigit():
            return SiteQueryMatch(target="fiction", lookup_type="id", identifier=raw)
        if "/" in raw:
            for part in (p.strip() for p in raw.split("/")):
                if part.isdigit():
                    return SiteQueryMatch(target="fiction", lookup_type="id", identifier=part)
        return None
