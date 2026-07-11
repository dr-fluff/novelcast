# novelcast/services/site_adapters/patreon.py

from typing import Optional
from urllib.parse import parse_qs, urlparse


def extract_creator(raw: str) -> Optional[str]:
    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").lower()

    if hostname not in {"patreon.com", "www.patreon.com"}:
        return None

    # handle ?vanity=
    query = parse_qs(parsed.query)
    vanity = (query.get("vanity") or [None])[0]
    if vanity:
        return vanity.strip()

    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None

    # normalize both /c/ and /cw/
    if parts[0].lower() in {"c", "cw"}:
        if len(parts) > 1:
            return parts[1]
        return None

    # fallback safety: ONLY if you are absolutely sure
    return None
