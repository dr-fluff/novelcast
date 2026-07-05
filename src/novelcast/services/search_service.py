import re
from dataclasses import dataclass
from typing import Optional

from novelcast.services.site_adapters import registry
from novelcast.services.site_adapters import patreon as patreon_adapter


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
    patreon_creator: Optional[str] = None
    patreon_route: Optional[str] = None 
    resolved_urls: Optional[list[str]] = None


@dataclass
class SearchResult:
    site: str
    kind: str   # fiction_search | author_search | fiction_detail | author_profile
    url: str
    label: Optional[str] = None
    patreon_url: Optional[str] = None
    patreon_creator: Optional[str] = None


# ---------------------------------------------------------------------------
# Parser / URL builder
# ---------------------------------------------------------------------------

class SearchService:

    def __init__(self, settings_service=None):
        """`settings_service` is optional — pass your SettingsService
        instance to make disabled sites invisible to search. Without it,
        every registered site is treated as enabled."""
        self._settings_service = settings_service

    def _enabled_sites(self) -> list[str]:
        return registry.enabled_sites(self._settings_service)

    def _patreon_enabled(self) -> bool:
        return registry.is_enabled("patreon", self._settings_service)

    def parse_query(self, raw: str) -> ParsedQuery:
        raw = raw.strip()

        # -------------------------
        # 1. PATREON URL / PREFIX
        # -------------------------
        if self._patreon_enabled():
            creator = patreon_adapter.extract_creator(raw)
            if creator:
                return ParsedQuery(
                    target="patreon",
                    identifier=creator,
                    lookup_type="patreon_url",
                    site="patreon",
                    patreon_creator=creator,
                    resolved_urls=self.build_patreon_urls(creator)
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
                    resolved_urls=self.build_patreon_urls(creator),
                )

        # -------------------------
        # 2. SITE-SPECIFIC FICTION / AUTHOR URL
        # -------------------------
        # Any adapter can recognize its own URLs here — adding a new site
        # only requires registering its adapter, not editing this method.
        for site in self._enabled_sites():
            adapter = registry.get_adapter(site)

            fid = adapter.match_fiction_url(raw)
            if fid:
                return ParsedQuery(
                    target="fiction",
                    identifier=fid,
                    lookup_type="url",
                    site=site,
                    resolved_url=adapter.fiction_url(fid),
                )

            aid = adapter.match_author_url(raw)
            if aid:
                return ParsedQuery(
                    target="author",
                    identifier=aid,
                    lookup_type="url",
                    site=site,
                    resolved_url=adapter.author_url(aid),
                )

        # -------------------------
        # 3. EXPLICIT FICTION
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
        # 4. EXPLICIT AUTHOR (including typos)
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
        # 5. NUMERIC ONLY (default = fiction)
        # -------------------------
        if raw.isdigit():
            return ParsedQuery(
                target="fiction",
                identifier=raw,
                lookup_type="id",
            )

        # -------------------------
        # 6. DEFAULT = AUTO (SEARCH BOTH FICTION & AUTHOR)
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

        if q.target == "patreon":
            if not self._patreon_enabled():
                return results
            creator = q.patreon_creator or q.identifier

            urls = [
                f"https://www.patreon.com/c/{creator}",
                f"https://www.patreon.com/cw/{creator}",
            ]

            results.extend(
                SearchResult(
                    site="patreon",
                    kind="author_profile",
                    url=url,
                    label=creator,
                    patreon_creator=creator,
                    patreon_url=url,
                )
                for url in urls
            )
            return results

        enabled = set(self._enabled_sites())
        if q.site:
            sites = [q.site] if q.site in enabled else []
        else:
            sites = list(enabled)

        for site in sites:
            adapter = registry.get_adapter(site)
            qtext = q.identifier.replace(" ", "+")

            if q.target == "author":
                if q.lookup_type == "id":
                    results.append(SearchResult(
                        site=site,
                        kind="author_profile",
                        url=adapter.author_url(q.identifier),
                    ))
                else:
                    results.append(SearchResult(
                        site=site,
                        kind="author_search",
                        url=adapter.author_search_url(qtext),
                    ))

            elif q.target == "fiction":
                if q.lookup_type == "id":
                    results.append(SearchResult(
                        site=site,
                        kind="fiction_detail",
                        url=adapter.fiction_url(q.identifier),
                    ))
                else:
                    results.append(SearchResult(
                        site=site,
                        kind="fiction_search",
                        url=adapter.fiction_search_url(qtext),
                    ))

            else:  # auto
                results.append(SearchResult(
                    site=site,
                    kind="fiction_search",
                    url=adapter.fiction_search_url(qtext),
                ))
                results.append(SearchResult(
                    site=site,
                    kind="author_search",
                    url=adapter.author_search_url(qtext),
                ))

        return results

    def build_patreon_urls(self, creator: str):
        return [
            f"https://www.patreon.com/c/{creator}",
            f"https://www.patreon.com/cw/{creator}",
        ]