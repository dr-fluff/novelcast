import asyncio
from types import SimpleNamespace

import httpx

from novelcast.api.routes import covers
from novelcast.api.routes.covers import _image_extension


def test_cover_download_uses_image_bytes_when_content_type_is_wrong():
    jpeg_data = b"\xff\xd8\xff\xe0" + b"image data"

    extension = _image_extension(jpeg_data, "image/png")

    assert extension == ".jpg"


def test_cover_url_is_saved_when_the_server_cannot_download_it(monkeypatch):
    class FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def get(self, _url):
            raise httpx.ConnectError("DNS lookup failed")

    class Stories:
        def __init__(self):
            self.cover_path = None

        def get_story(self, _story_id):
            return {"cover_path": self.cover_path}

        def update_story_cover(self, _story_id, cover_path):
            self.cover_path = cover_path

    emitted = []
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ctx=SimpleNamespace(emit=lambda *args: emitted.append(args)))))
    stories = Stories()
    monkeypatch.setattr(covers.httpx, "AsyncClient", lambda **_kwargs: FailingClient())

    result = asyncio.run(
        covers.set_cover_from_url(
            request,
            21,
            covers.CoverFromUrl(url="https://www.royalroadcdn.com/cover.jpg"),
            stories,
        )
    )

    assert result["status"] == "linked"
    assert stories.cover_path == "https://www.royalroadcdn.com/cover.jpg"
    assert emitted == [("story_updated", {"story_id": 21})]
