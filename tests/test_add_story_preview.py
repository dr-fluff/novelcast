import asyncio

from novelcast.api.routes.add_story import AddStoryRequest, preview_story_metadata


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad response")


class FakeAsyncClient:
    def __init__(self, html: str):
        self._html = html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, timeout=10.0, follow_redirects=True):
        return FakeResponse(self._html)


class DummyDownload:
    class orchestrator:
        @staticmethod
        def check_updates(url):
            raise RuntimeError("boom")

    def _extract_metadata(self, raw):
        return {}

class FakePatreonEngine:
    def list_posts_with_access(self, url, story_match=None):
        return {
            "creator": "MarvinKnight",
            "posts": [
                {
                    "number": 1,
                    "title": "First Post",
                    "locked": False,
                },
                {
                    "number": 2,
                    "title": "Second Post",
                    "locked": False,
                },
            ],
        }

def test_patreon_preview_uses_creator_page_posts_for_chapter_count(monkeypatch):
    html = """
    <html><head><title>Marvin Knight | Patreon</title></head>
    <body>
      <a href="/posts/first-post"><h3>First Post</h3></a>
      <a href="/posts/second-post"><h3>Second Post</h3></a>
    </body></html>
    """

    request = AddStoryRequest(url="https://www.patreon.com/c/MarvinKnight/home?vanity=MarvinKnight")
    result = asyncio.run(
        preview_story_metadata(
            request,
            download=DummyDownload(),
            patreon_engine=FakePatreonEngine(),
        )
    )

    assert result.title == "Patreon: MarvinKnight"
    assert result.author == "MarvinKnight"
    assert result.chapter_count == 2
    assert [chapter.title for chapter in result.chapters] == [
        "First Post",
        "Second Post",
    ]
