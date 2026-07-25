from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class SiteQueryMatch:
    """What a site adapter found when asked to interpret a raw search
    string. SearchService turns this straight into a ParsedQuery — it
    never inspects `raw` itself for site-specific patterns."""

    target: str  # "fiction" | "author"
    lookup_type: str  # "id" | "text" | "url"
    identifier: str
    resolved_url: Optional[str] = None


@runtime_checkable
class SiteAdapter(Protocol):
    """Everything SearchService needs to know about a fiction site.

    Adding a new site = writing one of these + registering it in
    `site_adapters/registry.py`. SearchService never special-cases a
    site by name — it only ever calls these methods.
    """

    name: str

    # Trigger words for a "prefix:identifier" query, e.g.
    # RoyalRoadAdapter -> ("royalroad", "rr"). Checked case-insensitively,
    # no trailing colon.
    query_prefixes: tuple[str, ...]

    def match_fiction_url(self, raw: str) -> Optional[str]:
        """Return the fiction id if `raw` is a fiction-detail URL for this site."""
        ...

    def match_author_url(self, raw: str) -> Optional[str]:
        """Return the author id if `raw` is an author/profile URL for this site."""
        ...

    def fiction_url(self, identifier: str) -> str: ...
    def author_url(self, identifier: str) -> str: ...
    def fiction_search_url(self, query_text: str) -> str: ...
    def author_search_url(self, query_text: str) -> str: ...

    def parse_identifier(self, remainder: str) -> SiteQueryMatch:
        """Interpret text with this site's prefix already stripped
        (the 'X' in 'rr:X'). Always returns a match — once a prefix is
        claimed, the remainder unambiguously belongs to this site."""
        ...

    def match_bare(self, raw: str) -> Optional[SiteQueryMatch]:
        """Try to interpret an un-prefixed, non-URL query as belonging
        to this site (e.g. RoyalRoad/ScribbleHub's shared '{id}/{name}'
        shorthand, or a bare numeric id). Return None if this site has
        no bare-query convention or `raw` doesn't fit it."""
        ...
