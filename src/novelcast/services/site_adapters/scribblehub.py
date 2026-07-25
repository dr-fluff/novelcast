import re
from typing import Optional

from .base import SiteQueryMatch


class ScribbleHubAdapter:
    name = "scribblehub"
    query_prefixes = ("scribblehub", "scribelhub", "s")

    def match_fiction_url(self, raw: str) -> Optional[str]:
        # TODO: verify against real ScribbleHub series URLs, e.g.
        # https://www.scribblehub.com/series/123456/some-slug/
        m = re.match(r"https?://.*scribblehub\.com/series/(\d+)", raw)
        return m.group(1) if m else None

    def match_author_url(self, raw: str) -> Optional[str]:
        # TODO: verify against real ScribbleHub profile URLs
        m = re.match(r"https?://.*scribblehub\.com/profile/(\d+)", raw)
        return m.group(1) if m else None

    def fiction_url(self, identifier: str) -> str:
        return f"https://www.scribblehub.com/series/{identifier}/"

    def author_url(self, identifier: str) -> str:
        return f"https://www.scribblehub.com/profile/{identifier}/"

    def fiction_search_url(self, query_text: str) -> str:
        return f"https://www.scribblehub.com/?s={query_text}&post_type=fictionposts"

    def author_search_url(self, query_text: str) -> str:
        return f"https://www.scribblehub.com/?s={query_text}&post_type=fictionposts"

    def parse_identifier(self, remainder: str) -> SiteQueryMatch:
        for part in (p.strip() for p in remainder.split("/")):
            if part.isdigit():
                return SiteQueryMatch(target="fiction", lookup_type="id", identifier=part)
        return SiteQueryMatch(target="fiction", lookup_type="text", identifier=remainder.strip())

    def match_bare(self, raw: str) -> Optional[SiteQueryMatch]:
        if raw.isdigit():
            return SiteQueryMatch(target="fiction", lookup_type="id", identifier=raw)
        if "/" in raw:
            for part in (p.strip() for p in raw.split("/")):
                if part.isdigit():
                    return SiteQueryMatch(target="fiction", lookup_type="id", identifier=part)
        return None
