# novelcast/services/scrapers/__init__.py
"""
Scraper orchestration with per-site enable/disable support.
"""

import asyncio

import httpx

from novelcast.services.search_service import SearchResult
from novelcast.services.site_adapters import registry
from novelcast.services.site_adapters.patreon import extract_creator as extract_patreon_creator
from novelcast.core import setting_keys

from . import patreon, royalroad, scribblehub
from .base import ScrapedResult
from .utils import normalize

_SCRAPERS = {
    "royalroad": royalroad,
    "scribblehub": scribblehub,
}

_KIND_METHOD = {
    "fiction_search": "scrape_fiction_search",
    "author_search": "scrape_author_search",
    "fiction_detail": "scrape_fiction_detail",
    "author_profile": "scrape_author_detail",
    "fiction": "scrape_fiction_detail",
    "author": "scrape_author_detail",
}




def _build_task(client: httpx.AsyncClient, sr, settings_service=None):
    if not registry.is_enabled(sr.site, settings_service):
        return None

    if sr.site == "patreon":
        creator = extract_patreon_creator(sr.url)
        if not creator:
            return None

        session_cookie = None
        if settings_service:
            session_cookie = settings_service.get(
                setting_keys.PATREON_SETTINGS.SESSION_COOKIE, default=None
            ).value

        return patreon.scrape_patreon_creator(client, creator, session_cookie=session_cookie)

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