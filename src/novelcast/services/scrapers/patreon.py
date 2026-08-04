# novelcast/services/scrapers/patreon.py
"""
Patreon scraper - extract available posts/stories from a creator's page
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from novelcast.services.site_adapters.patreon import PatreonAdapter

from .base import ScrapedResult

logger = logging.getLogger(__name__)

_adapter = PatreonAdapter()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.patreon.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}


async def scrape_patreon_creator(
    client: httpx.AsyncClient,
    creator_name: str,
    session_cookie: str | None = None,
) -> list[ScrapedResult]:
    """
    Scrape a Patreon creator's page to find available stories/posts.

    Args:
        client: httpx async client
        creator_name: Username (e.g., "brianjnordon")
        session_cookie: Optional Patreon session_id cookie value, from
            settings.PATREON_SETTINGS.SESSION_COOKIE — some creator pages
            render more (or only work at all) when the request looks
            like a logged-in session.

    Returns:
        List of ScrapedResult objects representing available posts
    """

    url = _adapter.author_url(creator_name)
    fallback_url = f"https://www.patreon.com/{creator_name}"

    headers = dict(HEADERS)
    cookies = {"session_id": session_cookie} if session_cookie else None

    try:
        resp = await client.get(url, headers=headers, cookies=cookies, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("[Patreon] Failed to fetch %s: %s", url, e)
        try:
            fallback_resp = await client.get(
                fallback_url,
                headers=headers,
                cookies=cookies,
                timeout=15.0,
                follow_redirects=True,
            )
            fallback_resp.raise_for_status()
            resp = fallback_resp
            url = fallback_url
        except httpx.HTTPError as fallback_error:
            logger.warning("[Patreon] Fallback fetch also failed for %s: %s", fallback_url, fallback_error)
            return []

    soup = BeautifulSoup(resp.text, "html.parser")

    creator_title = soup.select_one("title")
    creator_display = creator_name

    if creator_title:
        title_text = creator_title.get_text(" ", strip=True)
        if title_text:
            creator_display = re.sub(r"\s*\|\s*Patreon.*$", "", title_text).strip() or creator_name

    results = []

    post_links = soup.select('a[href*="/posts/"]')
    for link in post_links[:20]:
        href = link.get("href", "").strip()
        if not href or "/posts/" not in href:
            continue

        title_el = link.select_one('h3, .post-title, [class*="title"]')
        title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)

        if not title or len(title.strip()) < 2:
            continue

        if href.startswith("http"):
            post_url = href
        elif href.startswith("/"):
            post_url = f"https://www.patreon.com{href}"
        else:
            post_url = f"https://www.patreon.com/{href}"

        results.append(
            ScrapedResult(
                site="patreon",
                kind="fiction_search",
                url=post_url,
                title=title[:200],
                author=creator_display,
                description=f"Patreon post by {creator_display}",
                patreon_url=url,
            )
        )

    if not results:
        logger.info("[Patreon] No post links found on %s (page may require login, or markup changed)", url)
        fallback_title = f"Patreon: {creator_display}" if creator_display else f"Patreon creator {creator_name}"
        results.append(
            ScrapedResult(
                site="patreon",
                kind="author_profile",
                url=url,
                title=fallback_title,
                author=creator_display,
                description=f"Open {creator_display}'s Patreon page to browse available posts and rewards",
                patreon_url=url,
            )
        )

    return results
