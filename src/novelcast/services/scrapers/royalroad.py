# novelcast/services/scrapers/royalroad.py

import httpx
from bs4 import BeautifulSoup

from .base import ScrapedResult

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelCast/1.0)",
}


async def scrape_fiction_search(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")
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
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")
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
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

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
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

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
