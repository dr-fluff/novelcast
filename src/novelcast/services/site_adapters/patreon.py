from urllib.parse import parse_qs, urlparse

from .base import SiteQueryMatch

# Path segments that are Patreon UI routes, never a creator's vanity
# name — guards the bare-vanity fallback from misfiring on e.g.
# patreon.com/login
_RESERVED_SEGMENTS = {"home", "search", "login", "signup", "join", "settings", "explore"}


def extract_creator(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    hostname = (parsed.hostname or "").lower()

    if not hostname:
        # No scheme given (e.g. "patreon.com/creator") — retry with one.
        parsed = urlparse(f"https://{raw}")
        hostname = (parsed.hostname or "").lower()

    if hostname not in {"patreon.com", "www.patreon.com"}:
        return None

    query = parse_qs(parsed.query)
    vanity = (query.get("vanity") or [None])[0]
    if vanity:
        return vanity.strip().lower()

    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None

    first = parts[0].lower()

    # /c/{creator} or /cw/{creator} — covers /posts, /collections, and
    # any deeper path since we only look at the segment right after c/cw.
    if first in {"c", "cw"}:
        if len(parts) > 1:
            return parts[1].lower()
        return None

    if first in _RESERVED_SEGMENTS:
        return None

    # Bare vanity URL, e.g. patreon.com/{creator} or
    # patreon.com/{creator}/posts/some-specific-post-title-162751278
    return first


class PatreonAdapter:
    name = "patreon"
    query_prefixes = ("patreon", "p")

    def match_fiction_url(self, raw: str) -> str | None:
        return None  # Patreon has no per-title URL distinct from the creator page

    def match_author_url(self, raw: str) -> str | None:
        return extract_creator(raw)

    def fiction_url(self, identifier: str) -> str:
        return self.author_url(identifier)

    def author_url(self, identifier: str) -> str:
        # Always build the /c/ form — Patreon transparently redirects to
        # /cw/ for accounts that need it, so we never have to guess which
        # prefix a creator actually uses. /posts pins the URL to the
        # creator's post feed so we never resolve to a single post or a
        # collections page, which would look like the wrong "story".
        return f"https://www.patreon.com/c/{identifier}/posts"

    def fiction_search_url(self, query_text: str) -> str:
        return self.author_search_url(query_text)

    def author_search_url(self, query_text: str) -> str:
        # No public "search by name" endpoint on Patreon — treat the
        # query text itself as the creator's vanity name.
        return self.author_url(query_text)

    def parse_identifier(self, remainder: str) -> SiteQueryMatch:
        creator = extract_creator(remainder) or remainder.strip().lower()
        return SiteQueryMatch(target="author", lookup_type="id", identifier=creator)

    def match_bare(self, raw: str) -> SiteQueryMatch | None:
        return None  # bare creator names fall through to the generic auto-search
