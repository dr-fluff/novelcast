from typing import Optional


class ScribbleHubAdapter:
    name = "scribblehub"

    def match_fiction_url(self, raw: str) -> Optional[str]:
        # TODO: verify against real ScribbleHub series URLs, e.g.
        # https://www.scribblehub.com/series/123456/some-slug/
        import re
        m = re.match(r"https?://.*scribblehub\.com/series/(\d+)", raw)
        return m.group(1) if m else None

    def match_author_url(self, raw: str) -> Optional[str]:
        # TODO: verify against real ScribbleHub profile URLs
        import re
        m = re.match(r"https?://.*scribblehub\.com/profile/(\d+)", raw)
        return m.group(1) if m else None

    def fiction_url(self, identifier: str) -> str:
        return f"https://www.scribblehub.com/series/{identifier}/"

    def author_url(self, identifier: str) -> str:
        return f"https://www.scribblehub.com/profile/{identifier}/"

    def fiction_search_url(self, query_text: str) -> str:
        return f"https://www.scribblehub.com/?s={query_text}&post_type=fictionposts"

    def author_search_url(self, query_text: str) -> str:
        return f"https://www.scribblehub.com/?s={query_text}&post_type=fictionposts"