# novelcast/services/scrapers/base.py

from dataclasses import dataclass


@dataclass
class ScrapedResult:
    site: str
    kind: str  # "fiction" | "author"
    title: str
    author: str | None = None
    cover_url: str | None = None
    description: str | None = None
    url: str = ""
    patreon_url: str | None = None
