# novelcast/services/scrapers/royalroad.py

import logging
import os

import httpx
from bs4 import BeautifulSoup

from .base import ScrapedResult

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelCast/1.0)",
}

# Royal Road sits behind Anubis, which blocks plain HTTP clients. Pages are
# fetched through the local FlareSolverr-compatible shim (anubis_shim.py).
SHIM_URL = os.environ.get("NOVELCAST_ANUBIS_SHIM_URL", "http://127.0.0.1:8192/v1")
SHIM_TIMEOUT_MS = 60000


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str:
    """Return page HTML via the Anubis shim; fall back to a direct request if the shim fails."""
    try:
        resp = await client.post(
            SHIM_URL,
            json={"cmd": "request.get", "url": url, "maxTimeout": SHIM_TIMEOUT_MS},
            timeout=(SHIM_TIMEOUT_MS / 1000) + 10,
        )
        data = resp.json()
        if data.get("status") == "ok":
            return data["solution"]["response"]
        logger.warning("Anubis shim returned an error for %s: %s", url, data.get("message"))
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("Anubis shim request failed for %s: %s", url, e)

    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    return resp.text


async def scrape_fiction_search(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    html = await _fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for row in soup.select(".fiction-list-item"):
        title_el = row.select_one(".fiction-title")
        author_el = row.select_one(".author-name") or row.select_one("[title~='by']")
        cover_el = row.select_one("img")
        desc_el = row.select_one(".fiction-description, .description")
        link_el = row.select_one("a[href*='/fiction/']")

        if not title_el or not link_el:
            continue

        results.append(
            ScrapedResult(
                site="royalroad",
                kind="fiction",
                title=title_el.get_text(strip=True),
                author=author_el.get_text(strip=True) if author_el else None,
                cover_url=cover_el.get("src") if cover_el else None,
                description=desc_el.get_text(strip=True)[:300] if desc_el else None,
                url="https://www.royalroad.com" + link_el["href"],
            )
        )

    return results


async def scrape_author_search(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    html = await _fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for row in soup.select(".fiction-list-item"):
        title_el = row.select_one(".fiction-title")
        author_el = row.select_one(".author-name")
        cover_el = row.select_one("img")
        desc_el = row.select_one(".fiction-description, .description")
        link_el = row.select_one("a[href*='/fiction/']")

        if not title_el or not link_el:
            continue

        results.append(
            ScrapedResult(
                site="royalroad",
                kind="fiction",
                title=title_el.get_text(strip=True),
                author=author_el.get_text(strip=True) if author_el else None,
                cover_url=cover_el.get("src") if cover_el else None,
                description=desc_el.get_text(strip=True)[:300] if desc_el else None,
                url="https://www.royalroad.com" + link_el["href"],
            )
        )

    return results


async def scrape_fiction_detail(client: httpx.AsyncClient, url: str) -> ScrapedResult | None:
    """Scrape a single fiction page for cover, title, author, description."""
    html = await _fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one(".fiction-title, h1.font-white")
    author_el = soup.select_one("a[href*='/profile/']")
    cover_el = soup.select_one(".cover-art img, img.thumbnail")
    desc_el = soup.select_one(".description .prose, .fiction-description")

    if not title_el:
        return None

    return ScrapedResult(
        site="royalroad",
        kind="fiction",
        title=title_el.get_text(strip=True),
        author=author_el.get_text(strip=True) if author_el else None,
        cover_url=cover_el.get("src") if cover_el else None,
        description=desc_el.get_text(strip=True)[:300] if desc_el else None,
        url=url,
    )


async def scrape_author_detail(client: httpx.AsyncClient, url: str):
    html = await _fetch_html(client, url)
    soup = BeautifulSoup(html, "html.parser")

    results = []

    # RoyalRoad author pages reliably contain fiction links
    for link in soup.select("a[href*='/fiction/']"):
        href = link.get("href")
        if not href:
            continue

        full_url = "https://www.royalroad.com" + href

        results.append(
            ScrapedResult(
                site="royalroad",
                kind="fiction",
                title=link.get_text(strip=True),
                url=full_url,
            )
        )

    # remove duplicates
    unique = {r.url: r for r in results}

    return list(unique.values())


# end of file