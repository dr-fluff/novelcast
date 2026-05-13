# novelcast/utils/url_normalizer.py

import re


def normalize_story_url(url: str) -> str:
    # RoyalRoad canonicalization
    if "royalroad.com" in url:
        match = re.search(r"/fiction/(\d+)", url)
        if match:
            return f"https://www.royalroad.com/fiction/{match.group(1)}"

    return url.rstrip("/")