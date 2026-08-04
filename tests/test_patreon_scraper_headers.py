import asyncio

import httpx

from novelcast.services.scrapers.patreon import HEADERS, scrape_patreon_creator


class DummyResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=httpx.Request("GET", "https://example.com"), response=httpx.Response(self.status_code, request=httpx.Request("GET", "https://example.com")))


class DummyClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError("No more responses")
        return self.responses.pop(0)


def test_scraper_sends_browser_like_headers():
    client = DummyClient([DummyResponse("<html><title>Example</title><a href='/posts/123'>Post</a></html>")])

    results = asyncio.run(scrape_patreon_creator(client, "brianjnordon", session_cookie="abc"))

    assert results
    assert client.calls[0][1]["headers"]["User-Agent"] == HEADERS["User-Agent"]
    assert client.calls[0][1]["cookies"] == {"session_id": "abc"}


def test_scraper_returns_author_profile_when_requests_are_blocked():
    client = DummyClient([DummyResponse(status_code=403), DummyResponse(status_code=403)])

    results = asyncio.run(scrape_patreon_creator(client, "brianjnordon", session_cookie="abc"))

    assert results
    assert results[0].kind == "author_profile"
    assert results[0].url == "https://www.patreon.com/c/brianjnordon/posts"
    assert results[0].patreon_url == "https://www.patreon.com/c/brianjnordon/posts"


def test_scraper_rejects_malformed_creator_values():
    client = DummyClient([])

    results = asyncio.run(scrape_patreon_creator(client, '{"timestamp": "2026-08-04"}'))

    assert results
    assert results[0].kind == "author_profile"
    assert client.calls == []
