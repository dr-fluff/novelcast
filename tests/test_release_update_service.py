from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from novelcast.api.routes import admin as admin_routes
from novelcast.api.routes.utils import require_admin
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


def test_refresh_bypasses_the_release_cache():
    versions = iter(["v1.2.0", "v1.3.0"])

    def get(url, **kwargs):
        tag = next(versions)
        return FakeResponse({"tag_name": tag, "html_url": f"https://example.test/{tag}"})

    service = ReleaseUpdateService("dr-fluff/novelcast", current_version="1.1.0", http_get=get)

    assert service.get_available_update().latest_version == "v1.2.0"
    assert service.get_available_update(refresh=True).latest_version == "v1.3.0"


def test_admin_update_starts_the_latest_release_tag(monkeypatch, tmp_path):
    repo_dir = tmp_path / "repo"
    package_init = repo_dir / "src" / "novelcast" / "api" / "routes" / "admin" / "__init__.py"
    package_init.parent.mkdir(parents=True)
    (repo_dir / ".git").mkdir(parents=True)
    update_script = repo_dir / "scripts" / "update.sh"
    update_script.parent.mkdir()
    update_script.touch()

    monkeypatch.setattr(admin_routes, "__file__", str(package_init))
    original_exists = Path.exists

    def exists(path):
        if path == Path("/.dockerenv"):
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists)
    launched = []
    monkeypatch.setattr(admin_routes.subprocess, "Popen", lambda *args, **kwargs: launched.append((args, kwargs)))

    class FakeReleaseUpdates:
        repository = "dr-fluff/novelcast"

        def get_available_update(self, *, refresh=False):
            assert refresh is True
            return SimpleNamespace(latest_version="v1.4.0")

    app = FastAPI()
    app.include_router(admin_routes.router, prefix="/api/admin")
    app.state.release_updates = FakeReleaseUpdates()
    app.dependency_overrides[require_admin] = lambda: {"id": 1, "is_root": True}

    response = TestClient(app).post("/api/admin/update")

    assert response.status_code == 200
    assert "Updating to NovelCast v1.4.0" in response.text
    assert launched[0][0][0] == ["bash", str(update_script), "v1.4.0", "dr-fluff/novelcast"]
    assert launched[0][1]["start_new_session"] is True
