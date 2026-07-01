# novelcast/services/scrapers/__init__.py
"""
Scraper orchestration with Patreon support
"""

import asyncio
import httpx

from .base import ScrapedResult
from . import royalroad, scribblehub, patreon
from .utils import normalize
from novelcast.services.search_service import SearchResult

_SCRAPERS = {
    "royalroad":   royalroad,
    "scribblehub": scribblehub,
    "patreon":     patreon,
}


async def scrape_all(search_urls):
    """Scrape all search URLs and return combined results"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []

        for sr in search_urls:
            sr = normalize(sr)

            scraper = _SCRAPERS.get(sr.site)
            if not scraper:
                continue

            if sr.site == "patreon":
                creator = getattr(sr, "patreon_creator", None) or getattr(sr, "label", None)
                if creator:
                    tasks.append(patreon.scrape_patreon_creator(client, creator))
                else:
                    tasks.append(patreon.scrape_patreon_creator(client, sr.url.split("/")[-1]))
            else:
                match sr.kind:
                    case "fiction_search":
                        tasks.append(scraper.scrape_fiction_search(client, sr.url))

                    case "author_search":
                        tasks.append(scraper.scrape_author_search(client, sr.url))

                    case "fiction_detail":
                        tasks.append(scraper.scrape_fiction_detail(client, sr.url))

                    case "author_profile":
                        tasks.append(scraper.scrape_author_detail(client, sr.url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []
    for r in results:
        if isinstance(r, Exception):
            continue
        if isinstance(r, list):
            combined.extend(r)
        else:
            combined.append(r)

    return combined


async def scrape_details(search_urls: list[SearchResult]) -> list[ScrapedResult]:
    """Scrape individual fiction/author pages for full metadata."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for sr in search_urls:
            sr = normalize(sr)
            scraper = _SCRAPERS.get(sr.site)
            
            if scraper is None:
                continue
            
            # Handle Patreon specially
            if sr.site == "patreon":
                # For Patreon, we need the creator name, not a detail URL
                # Extract it from the normalized SR or the URL
                if hasattr(sr, 'patreon_creator'):
                    tasks.append(patreon.scrape_patreon_creator(client, sr.patreon_creator))
                else:
                    # Fall back to scraping from URL
                    tasks.append(patreon.scrape_patreon_post(client, sr.url))
            
            elif sr.kind == "fiction":
                tasks.append(scraper.scrape_fiction_detail(client, sr.url))
            elif sr.kind == "author":
                tasks.append(scraper.scrape_author_detail(client, sr.url))

        raw = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []
    for r in raw:
        if isinstance(r, Exception) or r is None:
            continue
        if isinstance(r, list):
            combined.extend(r)
        else:
            combined.append(r)

    return combined