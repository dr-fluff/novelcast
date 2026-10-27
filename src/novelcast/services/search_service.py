import re
from dataclasses import dataclass

from novelcast.services.site_adapters import registry

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ParsedQuery:
    target: str
    identifier: str
    lookup_type: str
    site: str | None = None
    resolved_url: str | None = None

    @property
    def id_type(self) -> str:
        """Compatibility with older templates and callers."""
        if self.target == "auto":
            return "title_and_author"
        if self.target == "author":
            return "author"
        if self.lookup_type == "id":
            return "numeric_id"
        if self.lookup_type == "url":
            return "numeric_id" if self.identifier.isdigit() else "author"
        return "title"

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
        if self._settings_service is None:
            return registry.all_sites()
        return registry.enabled_sites(self._settings_service)

    def parse_query(self, raw: str) -> ParsedQuery:
        raw = raw.strip()

        # Site prefix, optionally followed by a nested target:
        # rr:12345, rr:author:Mecanimus, scribblehub:Changeling
        m = re.match(r"^(?!https?://)([a-zA-Z -]+?)\s*:\s*(.+)$", raw, re.IGNORECASE)
        if m:
            prefix = re.sub(r"[\s-]+", "", m.group(1).lower())
            remainder = m.group(2).strip()

            # Generic search prefixes.
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

            # Resolve site aliases independently of enabled state.
            site = registry.resolve_alias(prefix)
            if site is None:
                raise ValueError(f"Unknown site prefix: {m.group(1).strip()}")

            adapter = registry.get_adapter(site)

            # Support nested author prefixes such as rr:author:Mecanimus.
            nested = re.match(
                r"^(author|authur|arthur|profile)\s*:\s*(.+)$",
                remainder,
                re.IGNORECASE,
            )
            if nested:
                identifier = nested.group(2).strip()
                return ParsedQuery(
                    target="author",
                    identifier=identifier,
                    lookup_type="id" if identifier.isdigit() else "text",
                    site=site,
                )

            match = adapter.parse_identifier(remainder)
            resolved_url = match.resolved_url
            if match.lookup_type == "id":
                if match.target == "author":
                    resolved_url = adapter.author_url(match.identifier)
                else:
                    resolved_url = adapter.fiction_url(match.identifier)

            return ParsedQuery(
                target=match.target,
                identifier=match.identifier,
                lookup_type=match.lookup_type,
                site=site,
                resolved_url=resolved_url,
            )

        # Direct URLs: check every adapter, not just enabled sites.
        for site in registry.all_sites():
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

        # Bare IDs recognized by an adapter.
        for site in self._enabled_sites():
            adapter = registry.get_adapter(site)
            match = adapter.match_bare(raw)
            if match:
                return ParsedQuery(
                    target=match.target,
                    identifier=match.identifier,
                    lookup_type=match.lookup_type,
                    site=site,
                    resolved_url=match.resolved_url,
                )

        return ParsedQuery(target="auto", identifier=raw, lookup_type="text")

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
                if q.lookup_type in {"id", "url"}:
                    _add(
                        SearchResult(
                            site=site,
                            kind="author_profile",
                            url=q.resolved_url or adapter.author_url(q.identifier),
                        )
                    )
                else:
                    _add(
                        SearchResult(
                            site=site,
                            kind="author_search",
                            url=adapter.author_search_url(q.identifier.replace(" ", "+")),
                        )
                    )
            elif q.target == "fiction":
                if q.lookup_type in {"id", "url"}:
                    _add(
                        SearchResult(
                            site=site,
                            kind="fiction_detail",
                            url=q.resolved_url or adapter.fiction_url(q.identifier),
                        )
                    )
                else:
                    _add(
                        SearchResult(
                            site=site,
                            kind="fiction_search",
                            url=adapter.fiction_search_url(q.identifier.replace(" ", "+")),
                        )
                    )
            else:
                qtext = q.identifier.replace(" ", "+")
                _add(
                    SearchResult(
                        site=site,
                        kind="fiction_search",
                        url=adapter.fiction_search_url(qtext),
                    )
                )
                _add(
                    SearchResult(
                        site=site,
                        kind="author_search",
                        url=adapter.author_search_url(qtext),
                    )
                )
        return results
