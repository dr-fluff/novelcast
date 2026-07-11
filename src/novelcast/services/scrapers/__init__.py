# novelcast/services/scrapers/__init__.py
"""
Scraper orchestration with per-site enable/disable support.
"""

import asyncio

import httpx

from novelcast.services.search_service import SearchResult
from novelcast.services.site_adapters import registry

from . import patreon, royalroad, scribblehub
from .base import ScrapedResult
from .utils import normalize

_SCRAPERS = {
    "royalroad": royalroad,
    "scribblehub": scribblehub,
}

# SearchResult.kind -> scraper module method name
_KIND_METHOD = {
    "fiction_search": "scrape_fiction_search",
    "author_search": "scrape_author_search",
    "fiction_detail": "scrape_fiction_detail",
    "author_profile": "scrape_author_detail",
    # used by scrape_details() below
    "fiction": "scrape_fiction_detail",
    "author": "scrape_author_detail",
}


def _build_task(client: httpx.AsyncClient, sr, settings_service=None):
    """Return a coroutine for `sr`, or None if it should be skipped
    (site disabled, unknown site, or unknown kind)."""
    if not registry.is_enabled(sr.site, settings_service):
        return None

    if sr.site == "patreon":
        creator = getattr(sr, "patreon_creator", None)
        if not creator:
            creator = sr.url.rstrip("/").split("/")[-1]
        # Detail-page requests (scrape_details) hit a specific post URL;
        # search/profile requests want the creator's page.
        if sr.kind in ("fiction", "fiction_detail") and "/posts/" in sr.url:
            return patreon.scrape_patreon_post(client, sr.url)
        return patreon.scrape_patreon_creator(client, creator)

    scraper = _SCRAPERS.get(sr.site)
    if scraper is None:
        return None

    method_name = _KIND_METHOD.get(sr.kind)
    method = getattr(scraper, method_name, None) if method_name else None
    if method is None:
        return None

    return method(client, sr.url)


async def _gather(tasks):
    results = await asyncio.gather(*tasks, return_exceptions=True)
    combined = []
    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        if isinstance(r, list):
            combined.extend(r)
        else:
            combined.append(r)
    return combined


async def scrape_all(search_urls, settings_service=None):
    """Scrape all search URLs and return combined results.
    Sites disabled via settings_service are silently skipped."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            task
            for sr in (normalize(s) for s in search_urls)
            if (task := _build_task(client, sr, settings_service)) is not None
        ]
        return await _gather(tasks)


async def scrape_details(search_urls: list[SearchResult], settings_service=None) -> list[ScrapedResult]:
    """Scrape individual fiction/author pages for full metadata.
    Sites disabled via settings_service are silently skipped."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [
            task
            for sr in (normalize(s) for s in search_urls)
            if (task := _build_task(client, sr, settings_service)) is not None
        ]
        return await _gather(tasks)
