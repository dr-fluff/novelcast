# novelcast/services/scrapers/base.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapedResult:
    site: str
    kind: str                  # "fiction" | "author"
    title: str
    author: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    url: str = ""
    patreon_url: Optional[str] = None