# novelcast/services/scrapers/__init__.py

import asyncio
import httpx

from .base import ScrapedResult
from . import royalroad, scribblehub
from .utils import normalize
from novelcast.services.search_service import SearchResult

_SCRAPERS = {
    "royalroad":   royalroad,
    "scribblehub": scribblehub,
}


async def scrape_all(search_urls):
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []

        
        for sr in search_urls:
            sr = normalize(sr)

            scraper = _SCRAPERS.get(sr.site)
            if not scraper:
                continue

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
        combined.extend(r)

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
            if sr.kind == "fiction":
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