# novelcast/services/site_adapters/patreon.py

from typing import Optional
from urllib.parse import parse_qs, urlparse


def extract_creator(raw: str) -> Optional[str]:
    
    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"patreon.com", "www.patreon.com"}:
        return None

    query = parse_qs(parsed.query)
    vanity = (query.get("vanity") or [None])[0]
    if vanity:
        return vanity.strip()

    parts = [segment for segment in parsed.path.split("/") if segment]
    if not parts:
        return None

    if parts[0].lower() == "c" and len(parts) > 1:
        return parts[1]

    return parts[0]