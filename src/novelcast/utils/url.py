# novelcast/utils/url_.py

import re
from urllib.parse import urlparse


def normalize_story_url(url: str) -> str:
    # RoyalRoad canonicalization
    if "royalroad.com" in url:
        match = re.search(r"/fiction/(\d+)", url)
        if match:
            return f"https://www.royalroad.com/fiction/{match.group(1)}"

    return url.rstrip("/")


def get_site_from_url(url: str | None) -> str | None:
    if not url:
        return None

    hostname = urlparse(url).hostname

    if not hostname:
        return None

    hostname = hostname.lower()

    if "royalroad.com" in hostname:
        return "royalroad"

    if "scribblehub.com" in hostname:
        return "scribblehub"

    if "archiveofourown.org" in hostname:
        return "ao3"

    return None
