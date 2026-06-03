# novelcast/services/scrapers/base.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScrapedResult:
    site: str
    kind: str                  # "fiction" | "author"
    title: str
    author: Optional[str]
    cover_url: Optional[str]
    description: Optional[str]
    url: str