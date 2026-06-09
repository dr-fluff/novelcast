# novelcast/services/scrapers/patreon.py
"""
Patreon scraper - extract available posts/stories from a creator's page
"""

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
    
    # Extract creator info from page title or metadata
    creator_title = soup.select_one('title')
    creator_display = creator_name
    
    if creator_title:
        title_text = creator_title.get_text()
        # Extract creator display name from title (usually "Name | Patreon")
        if "|" in title_text:
            creator_display = title_text.split("|")[0].strip()
    
    results = []
    
    # Method 1: Look for post links in the page
    # Patreon posts are usually in <a> tags with href like /posts/12345678
    post_links = soup.select('a[href*="/posts/"]')
    
    for link in post_links[:20]:  # Limit to first 20 to avoid excessive results
        href = link.get('href', '').strip()
        if not href or '/posts/' not in href:
            continue
        
        # Extract post title
        title_el = link.select_one('h3, .post-title, [class*="title"]')
        title = title_el.get_text(strip=True) if title_el else link.get_text(strip=True)
        
        if not title or len(title.strip()) < 2:
            continue
        
        # Build full URL
        if href.startswith('http'):
            post_url = href
        elif href.startswith('/'):
            post_url = f"https://www.patreon.com{href}"
        else:
            post_url = f"https://www.patreon.com/{href}"
        
        # Create result
        result = ScrapedResult(
            site="patreon",
            kind="fiction_search",
            url=post_url,
            title=title[:200],
            author=creator_display,
            description=f"Patreon post by {creator_display}",
            patreon_url=url,
        )
        results.append(result)
    
    # If no posts found, return creator profile as a single result
    # (user can browse directly on Patreon)
    if not results:
        creator_result = ScrapedResult(
            site="patreon",
            kind="author_profile",
            url=url,
            title=f"Patreon: {creator_display}",
            author=creator_display,
            description=f"Visit {creator_display}'s Patreon to view stories",
            patreon_url=url,
        )
        results.append(creator_result)
    
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