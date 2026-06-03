# novelcast/services/scrapers/utils.py

from novelcast.services.search_service import SearchResult

def normalize(sr):
    if isinstance(sr, dict):
        return SearchResult(**sr)
    return sr