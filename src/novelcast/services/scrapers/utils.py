# novelcast/services/scrapers/utils.py
from typing import Union

from novelcast.services.search_service import SearchResult


def normalize(sr: Union[dict, SearchResult]) -> SearchResult:
    """Normalize a search result (dict or SearchResult) to a SearchResult."""
    if isinstance(sr, SearchResult):
        return sr

    if not isinstance(sr, dict):
        raise ValueError(f"Expected dict or SearchResult, got {type(sr)}")

    return SearchResult(
        site=sr.get("site", ""),
        kind=sr.get("kind", ""),
        url=sr.get("url", ""),
        label=sr.get("label"),
    )
