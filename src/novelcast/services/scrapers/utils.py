# novelcast/services/scrapers/utils.py

from novelcast.services.search_service import SearchResult
import re
from typing import Optional, Union

def normalize(sr):
    if isinstance(sr, dict):
        return SearchResult(**sr)
    return sr


def extract_patreon_creator(url: str) -> Optional[str]:
    """Extract creator name from Patreon URL
    
    Examples:
        https://www.patreon.com/DanielKensingtonAuthor → DanielKensingtonAuthor
        https://patreon.com/username → username
        https://www.patreon.com/username/home → username
    """
    m = re.match(r"https?://(?:www\.)?patreon\.com/([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else None


def normalize(sr: Union[dict, SearchResult]) -> SearchResult:
    """
    Normalize search result to standard SearchResult format.
    
    Handles:
    - Dict → SearchResult conversion
    - Patreon URL creator extraction
    - URL validation
    
    Args:
        sr: SearchResult dict or SearchResult object
    
    Returns:
        SearchResult object
    """
    if isinstance(sr, SearchResult):
        return sr
    
    if not isinstance(sr, dict):
        raise ValueError(f"Expected dict or SearchResult, got {type(sr)}")
    
    # Extract Patreon creator if dealing with Patreon URL
    patreon_creator = None
    if sr.get('site') == 'patreon' and sr.get('url'):
        patreon_creator = extract_patreon_creator(sr['url'])
    
    # Build SearchResult with all fields
    result = SearchResult(
        site=sr.get('site', ''),
        kind=sr.get('kind', ''),
        url=sr.get('url', ''),
        label=sr.get('label'),
        patreon_url=sr.get('patreon_url'),
    )
    
    # Store creator on result for later use
    if patreon_creator:
        result.patreon_creator = patreon_creator
    
    return result