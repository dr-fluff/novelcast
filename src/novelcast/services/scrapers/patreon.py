# novelcast/services/scrapers/patreon.py
"""
Patreon scraper - extract available posts/stories from a creator's page
"""

import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from .base import ScrapedResult


async def scrape_patreon_creator(client: httpx.AsyncClient, creator_name: str) -> List[ScrapedResult]:
    """
    Scrape a Patreon creator's page to find available stories/posts.
    
    Returns posts as searchable results that can be added to library via PatreonEngine.
    
    Args:
        client: httpx async client
        creator_name: Username (e.g., "DanielKensingtonAuthor")
    
    Returns:
        List of ScrapedResult objects representing available posts
    """
    
    url = f"https://www.patreon.com/{creator_name}"
    
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[Patreon] Failed to fetch {url}: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    creator_title = soup.select_one('title')
    creator_display = creator_name
    
    if creator_title:
        title_text = creator_title.get_text(" ", strip=True)
        if title_text:
            creator_display = re.sub(r"\s*\|\s*Patreon.*$", "", title_text).strip() or creator_name
    
    results = []
    
    post_links = soup.select('a[href*="/posts/"]')
    for link in post_links[:20]:
        href = link.get('href', '').strip()
        if not href or '/posts/' not in href:
            continue
        
        title_el = link.select_one('h3, .post-title, [class*="title"]')
        title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
        
        if not title or len(title.strip()) < 2:
            continue
        
        if href.startswith('http'):
            post_url = href
        elif href.startswith('/'):
            post_url = f"https://www.patreon.com{href}"
        else:
            post_url = f"https://www.patreon.com/{href}"
        
        results.append(ScrapedResult(
            site="patreon",
            kind="fiction_search",
            url=post_url,
            title=title[:200],
            author=creator_display,
            description=f"Patreon post by {creator_display}",
            patreon_url=url,
        ))
    
    if not results:
        # Fallback: create a creator result from the page metadata, so the UI
        # still shows something useful instead of an empty state for Patreon.
        fallback_title = f"Patreon: {creator_display}" if creator_display else f"Patreon creator {creator_name}"
        results.append(ScrapedResult(
            site="patreon",
            kind="author_profile",
            url=url,
            title=fallback_title,
            author=creator_display,
            description=f"Open {creator_display}'s Patreon page to browse available posts and rewards",
            patreon_url=url,
        ))
    
    return results


async def scrape_patreon_post(client: httpx.AsyncClient, post_url: str) -> Optional[ScrapedResult]:
    """
    Scrape a single Patreon post for details.
    
    Args:
        client: httpx async client
        post_url: Full URL to the post (e.g., https://www.patreon.com/posts/12345678)
    
    Returns:
        ScrapedResult with post details, or None if post not found
    """
    
    try:
        resp = await client.get(post_url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Extract post title
    title_el = soup.select_one('h1, .post-title, [class*="title"]')
    title = title_el.get_text(strip=True) if title_el else "Untitled"
    
    # Extract creator name
    creator_el = soup.select_one('a[href^="/"], [class*="creator"]')
    creator = creator_el.get_text(strip=True) if creator_el else "Unknown Creator"
    
    # Extract description/content preview
    content_el = soup.select_one('[class*="content"], .post-content, article')
    description = ""
    if content_el:
        description = content_el.get_text(strip=True)[:500]
    
    return ScrapedResult(
        site="patreon",
        kind="fiction_detail",
        url=post_url,
        title=title,
        author=creator,
        description=description,
        patreon_url=post_url,
    )