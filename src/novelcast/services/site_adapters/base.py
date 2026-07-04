# novelcast/services/site_adapters/base.py
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class SiteAdapter(Protocol):
    """Everything SearchService needs to know about a fiction site.

    Adding a new site = writing one of these + registering it in
    `site_adapters/registry.py`. SearchService and the scrapers
    orchestrator never need to change.
    """

    name: str

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