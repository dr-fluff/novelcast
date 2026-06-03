# novelcast/services/scrapers/scribblehub.py

import httpx
from bs4 import BeautifulSoup
from .base import ScrapedResult

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelCast/1.0)",
}


def _clean_cover(url: str | None) -> str | None:
    if not url:
        return None
    if "nocover" in url or "no-cover" in url:
        return None
    return url


async def scrape_fiction_search(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for row in soup.select(".search-body .novel-item, .s_novel_item"):
        title_el  = row.select_one(".title, .novel-title")
        author_el = row.select_one(".author, .novel-author")
        cover_el  = row.select_one("img")
        desc_el   = row.select_one(".desc, .novel-desc, .summary")
        link_el   = row.select_one("a[href*='/series/']")

        if not title_el or not link_el:
            continue

        results.append(ScrapedResult(
            site="scribblehub",
            kind="fiction",
            title=title_el.get_text(strip=True),
            author=author_el.get_text(strip=True) if author_el else None,
            cover_url=_clean_cover(cover_el.get("src") if cover_el else None),
            description=desc_el.get_text(strip=True)[:300] if desc_el else None,
            url=link_el["href"],
        ))

    return results


async def scrape_author_search(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for row in soup.select(".search-body .user-item, .s_user_item"):
        name_el   = row.select_one(".name, .username")
        avatar_el = row.select_one("img")
        link_el   = row.select_one("a[href*='/profile/']")

        if not name_el or not link_el:
            continue

        results.append(ScrapedResult(
            site="scribblehub",
            kind="author",
            title=name_el.get_text(strip=True),
            author=None,
            cover_url=_clean_cover(avatar_el.get("src") if avatar_el else None),
            description=None,
            url=link_el["href"],
        ))

    return results


async def scrape_fiction_detail(client: httpx.AsyncClient, url: str) -> ScrapedResult | None:
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    title_el  = soup.select_one(".fic-title h1, .novel-title")
    author_el = soup.select_one(".auth-name a, .novel-author a")
    cover_el  = soup.select_one(".novel-cover img, .fic-header img")
    desc_el   = soup.select_one(".summary .wi_fic_desc, .novel-desc")

    if not title_el:
        return None

    return ScrapedResult(
        site="scribblehub",
        kind="fiction",
        title=title_el.get_text(strip=True),
        author=author_el.get_text(strip=True) if author_el else None,
        cover_url=_clean_cover(cover_el.get("src") if cover_el else None),
        description=desc_el.get_text(strip=True)[:300] if desc_el else None,
        url=url,
    )


async def scrape_author_detail(client: httpx.AsyncClient, url: str) -> list[ScrapedResult]:
    """Scrape author profile page — returns their fictions."""
    resp = await client.get(url, headers=HEADERS, follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    author_el = soup.select_one(".g_title, .profile-name")

    for row in soup.select(".search-body .novel-item, .s_novel_item"):
        title_el = row.select_one(".title, .novel-title")
        cover_el = row.select_one("img")
        desc_el  = row.select_one(".desc, .novel-desc")
        link_el  = row.select_one("a[href*='/series/']")

        if not title_el or not link_el:
            continue

        results.append(ScrapedResult(
            site="scribblehub",
            kind="fiction",
            title=title_el.get_text(strip=True),
            author=author_el.get_text(strip=True) if author_el else None,
            cover_url=_clean_cover(cover_el.get("src") if cover_el else None),
            description=desc_el.get_text(strip=True)[:300] if desc_el else None,
            url=link_el["href"],
        ))

    return results