import re
from dataclasses import dataclass

from novelcast.services.site_adapters import registry

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ParsedQuery:
    target: str  # fiction | author | auto
    identifier: str
    lookup_type: str  # id | text | url
    site: str | None = None
    resolved_url: str | None = None


@dataclass
class SearchResult:
    site: str
    kind: str  # fiction_search | author_search | fiction_detail | author_profile
    url: str
    label: str | None = None


# ---------------------------------------------------------------------------
# Parser / URL builder
# ---------------------------------------------------------------------------

_GENERIC_FICTION_PREFIXES = {"story", "fiction", "fictions"}
_GENERIC_AUTHOR_PREFIXES = {"author", "authur", "arthur", "profile"}


class SearchService:
    def __init__(self, settings_service=None):
        """`settings_service` is optional — pass your SettingsService
        instance to make disabled sites invisible to search. Without it,
        every registered site is treated as enabled."""
        self._settings_service = settings_service

    def _enabled_sites(self) -> list[str]:
        return registry.enabled_sites(self._settings_service)

    def parse_query(self, raw: str) -> ParsedQuery:
        raw = raw.strip()

        # -------------------------
        # 1. "prefix:identifier" pinned to whichever enabled site owns
        #    that trigger word — the adapter decides what the remainder
        #    means. Falls through untouched if the prefix isn't a site's
        #    or a generic fiction/author word (e.g. "https://...").
        # -------------------------
        m = re.match(r"^([a-zA-Z]+)\s*:\s*(.+)$", raw)
        if m:
            prefix, remainder = m.group(1).lower(), m.group(2).strip()

            for site in self._enabled_sites():
                adapter = registry.get_adapter(site)
                if prefix in adapter.query_prefixes:
                    match = adapter.parse_identifier(remainder)
                    return ParsedQuery(
                        target=match.target,
                        identifier=match.identifier,
                        lookup_type=match.lookup_type,
                        site=site,
                        resolved_url=match.resolved_url,
                    )

            if prefix in _GENERIC_FICTION_PREFIXES:
                return ParsedQuery(
                    target="fiction",
                    identifier=remainder,
                    lookup_type="id" if remainder.isdigit() else "text",
                )

            if prefix in _GENERIC_AUTHOR_PREFIXES:
                return ParsedQuery(
                    target="author",
                    identifier=remainder,
                    lookup_type="id" if remainder.isdigit() else "text",
                )

        # -------------------------
        # 2. Direct URL recognized by any enabled site's own adapter.
        #    Adding a new site only requires registering its adapter —
        #    this loop never changes.
        # -------------------------
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
        # 3. Un-prefixed, non-URL shorthand a site recognizes on its own
        #    (e.g. RoyalRoad/ScribbleHub's shared "{id}/{name}" or bare id).
        # -------------------------
        for site in self._enabled_sites():
            adapter = registry.get_adapter(site)
            match = adapter.match_bare(raw)
            if match:
                return ParsedQuery(
                    target=match.target,
                    identifier=match.identifier,
                    lookup_type=match.lookup_type,
                )

        # -------------------------
        # 4. Default = free-text search across every enabled site.
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
        seen_urls = set()

        def _add(result: SearchResult):
            if result.url in seen_urls:
                return
            seen_urls.add(result.url)
            results.append(result)

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
                    _add(SearchResult(site=site, kind="author_profile", url=adapter.author_url(q.identifier)))
                else:
                    _add(SearchResult(site=site, kind="author_search", url=adapter.author_search_url(qtext)))

            elif q.target == "fiction":
                if q.lookup_type == "id":
                    _add(SearchResult(site=site, kind="fiction_detail", url=adapter.fiction_url(q.identifier)))
                else:
                    _add(SearchResult(site=site, kind="fiction_search", url=adapter.fiction_search_url(qtext)))

            else:  # auto
                _add(SearchResult(site=site, kind="fiction_search", url=adapter.fiction_search_url(qtext)))
                _add(SearchResult(site=site, kind="author_search", url=adapter.author_search_url(qtext)))

        return results
