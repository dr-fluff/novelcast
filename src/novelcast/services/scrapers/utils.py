# novelcast/services/scrapers/utils.py
from typing import Union

from novelcast.services.search_service import SearchResult
from novelcast.services.site_adapters.patreon import (
    extract_creator as extract_patreon_creator,
)


def normalize(sr: Union[dict, SearchResult]) -> SearchResult:
    """Normalize a search result to a SearchResult, filling in
    patreon_creator from the URL when it's missing."""
    if isinstance(sr, SearchResult):
        return sr

    if not isinstance(sr, dict):
        raise ValueError(f"Expected dict or SearchResult, got {type(sr)}")

    patreon_creator = sr.get("patreon_creator")
    if not patreon_creator and sr.get("site") == "patreon" and sr.get("url"):
        patreon_creator = extract_patreon_creator(sr["url"])

    return SearchResult(
        site=sr.get("site", ""),
        kind=sr.get("kind", ""),
        url=sr.get("url", ""),
        label=sr.get("label"),
        patreon_url=sr.get("patreon_url"),
        patreon_creator=patreon_creator,
    )
