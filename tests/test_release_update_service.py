from novelcast.services.release_update_service import ReleaseUpdateService


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self) -> dict:
        return self.payload


def test_reports_a_newer_github_release_and_caches_the_result():
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"tag_name": "v1.2.0", "html_url": "https://github.com/dr-fluff/novelcast/releases/tag/v1.2.0"})

    service = ReleaseUpdateService("dr-fluff/novelcast", current_version="1.1.0", http_get=get)

    update = service.get_available_update()

    assert update is not None
    assert update.latest_version == "v1.2.0"
    assert update.current_version == "1.1.0"
    assert service.get_available_update() == update
    assert len(calls) == 1


def test_does_not_report_the_same_or_an_older_release():
    service = ReleaseUpdateService(
        "dr-fluff/novelcast",
        current_version="1.2.0",
        http_get=lambda *args, **kwargs: FakeResponse({"tag_name": "v1.2.0", "html_url": "https://example.test/release"}),
    )

    assert service.get_available_update() is None
