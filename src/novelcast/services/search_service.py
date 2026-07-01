import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlparse


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuery:
    target: str            # fiction | author | auto | patreon
    identifier: str
    lookup_type: str       # id | text | url | patreon_url
    site: Optional[str] = None
    resolved_url: Optional[str] = None
    patreon_creator: Optional[str] = None  # Extracted from patreon.com/username


@dataclass
class SearchResult:
    site: str
    kind: str   # fiction_search | author_search | fiction_detail | author_profile
    url: str
    label: Optional[str] = None
    patreon_url: Optional[str] = None
    patreon_creator: Optional[str] = None

# ---------------------------------------------------------------------------
# Site registry (kept minimal now, adapters handle logic later)
# ---------------------------------------------------------------------------

SITE_REGISTRY = {
    "royalroad": {
        "fiction_url": "https://www.royalroad.com/fiction/{id}",
        "author_url": "https://www.royalroad.com/profile/{id}/fictions",
        "fiction_search": "https://www.royalroad.com/fictions/search?title={q}",
        "author_search": "https://www.royalroad.com/fictions/search?author={q}",
    }
}


ALIAS_MAP = {
    "rr": "royalroad",
    "royalroad": "royalroad",
}


def _extract_patreon_creator(raw: str) -> Optional[str]:
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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class SearchService:

    def parse_query(self, raw: str) -> ParsedQuery:
        raw = raw.strip()

        # -------------------------
        # 1. PATREON URL / PREFIX
        # -------------------------
        # Matches: https://www.patreon.com/username or https://patreon.com/username
        creator = _extract_patreon_creator(raw)
        if creator:
            return ParsedQuery(
                target="patreon",
                identifier=creator,
                lookup_type="patreon_url",
                site="patreon",
                patreon_creator=creator,
                resolved_url=f"https://www.patreon.com/{creator}",
            )

        m = re.match(r"^patreon\s*:\s*(.+)$", raw, re.I)
        if m:
            creator = m.group(1).strip()
            return ParsedQuery(
                target="patreon",
                identifier=creator,
                lookup_type="text",
                site="patreon",
                patreon_creator=creator,
                resolved_url=f"https://www.patreon.com/{creator}",
            )

        # -------------------------
        # 2. FULL FICTION URL
        # -------------------------
        m = re.match(r"https?://.*royalroad\.com/fiction/(\d+)", raw)
        if m:
            fid = m.group(1)
            return ParsedQuery(
                target="fiction",
                identifier=fid,
                lookup_type="url",
                site="royalroad",
                resolved_url=f"https://www.royalroad.com/fiction/{fid}",
            )

        # -------------------------
        # 3. AUTHOR URL (RoyalRoad profile)
        # -------------------------
        m = re.match(r"https?://.*royalroad\.com/profile/(\d+)", raw)
        if m:
            aid = m.group(1)
            return ParsedQuery(
                target="author",
                identifier=aid,
                lookup_type="url",
                site="royalroad",
                resolved_url=f"https://www.royalroad.com/profile/{aid}/fictions",
            )

        # -------------------------
        # 4. EXPLICIT FICTION
        # -------------------------
        m = re.match(r"^(story|fiction|fictions)\s*:\s*(.+)$", raw, re.I)
        if m:
            val = m.group(2).strip()
            return ParsedQuery(
                target="fiction",
                identifier=val,
                lookup_type="id" if val.isdigit() else "text",
            )

        # -------------------------
        # 5. EXPLICIT AUTHOR (including typos)
        # -------------------------
        m = re.match(r"^(author|authur|arthur|profile)\s*:\s*(.+)$", raw, re.I)
        if m:
            val = m.group(2).strip()

            return ParsedQuery(
                target="author",
                identifier=val,
                lookup_type="id" if val.isdigit() else "text",
            )

        # -------------------------
        # 6. NUMERIC ONLY (default = fiction)
        # -------------------------
        if raw.isdigit():
            return ParsedQuery(
                target="fiction",
                identifier=raw,
                lookup_type="id",
            )

        # -------------------------
        # 7. DEFAULT = AUTO (SEARCH BOTH FICTION & AUTHOR)
        # -------------------------
        return ParsedQuery(
            target="auto",
            identifier=raw,
            lookup_type="text",
        )

    # -----------------------------------------------------------------------
    # Build URLs
    # -----------------------------------------------------------------------

    def build_search_urls(self, q: ParsedQuery):
        results = []

        # ─────────────────────────────────────────────────────────────────
        # PATREON: Search for author's works on supported sites
        # ─────────────────────────────────────────────────────────────────
        if q.target == "patreon":
            creator = q.patreon_creator or q.identifier
            patreon_url = f"https://www.patreon.com/{creator}"
            results.append(SearchResult(
                site="patreon",
                kind="author_profile",
                url=patreon_url,
                label=creator,
                patreon_url=patreon_url,
                patreon_creator=creator,
            ))
            return results

        sites = (
            [q.site]
            if q.site
            else SITE_REGISTRY.keys()
        )

        for site in sites:
            cfg = SITE_REGISTRY[site]
            qtext = q.identifier.replace(" ", "+")

            # -------------------------
            # AUTHOR
            # -------------------------
            if q.target == "author":

                if q.lookup_type == "id":
                    results.append(SearchResult(
                        site=site,
                        kind="author_profile",
                        url=cfg["author_url"].format(id=q.identifier),
                    ))

                else:
                    results.append(SearchResult(
                        site=site,
                        kind="author_search",
                        url=cfg["author_search"].format(q=qtext),
                    ))

            # -------------------------
            # FICTION
            # -------------------------
            elif q.target == "fiction":

                if q.lookup_type == "id":
                    results.append(SearchResult(
                        site=site,
                        kind="fiction_detail",
                        url=cfg["fiction_url"].format(id=q.identifier),
                    ))

                else:
                    results.append(SearchResult(
                        site=site,
                        kind="fiction_search",
                        url=cfg["fiction_search"].format(q=qtext),
                    ))

            # -------------------------
            # AUTO MODE (BOTH FICTION & AUTHOR)
            # -------------------------
            else:
                results.append(SearchResult(
                    site=site,
                    kind="fiction_search",
                    url=cfg["fiction_search"].format(q=qtext),
                ))
                results.append(SearchResult(
                    site=site,
                    kind="author_search",
                    url=cfg["author_search"].format(q=qtext),
                ))

        return results