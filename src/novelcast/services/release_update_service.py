"""Cached GitHub release checks for the administrator update notice."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

import httpx

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)*)$")


@dataclass(frozen=True)
class ReleaseUpdate:
    current_version: str
    latest_version: str
    release_url: str


def installed_version() -> str:
    """Return the installed package version, including editable installs."""
    try:
        return version("novelcast")
    except PackageNotFoundError:
        return "0.0.0"


def _version_key(value: str) -> tuple[int, ...] | None:
    """Parse normal release tags (``v1.2.3`` / ``1.2.3``) for comparison."""
    match = _VERSION_RE.fullmatch(value.strip().split("+", 1)[0].split("-", 1)[0])
    if not match:
        return None
    parts = tuple(int(part) for part in match.group(1).split("."))
    return parts + (0,) * (3 - len(parts))


class ReleaseUpdateService:
    """Check GitHub Releases at most once per cache period.

    The check runs only while preparing an admin template context. Regular
    users never cause a request to GitHub and never receive release metadata.
    """

    def __init__(
        self,
        repository: str | None,
        *,
        current_version: str | None = None,
        cache_seconds: int = 6 * 60 * 60,
        http_get: Callable = httpx.get,
    ):
        self.repository = repository.strip("/") if repository else ""
        self.current_version = current_version or installed_version()
        self.cache_seconds = cache_seconds
        self._http_get = http_get
        self._checked_at = 0.0
        self._cached_update: ReleaseUpdate | None = None
        self._lock = threading.Lock()

    def get_available_update(self) -> ReleaseUpdate | None:
        if not self.repository:
            return None

        with self._lock:
            if time.monotonic() - self._checked_at < self.cache_seconds:
                return self._cached_update

            self._checked_at = time.monotonic()
            self._cached_update = self._fetch_available_update()
            return self._cached_update

    def _fetch_available_update(self) -> ReleaseUpdate | None:
        try:
            response = self._http_get(
                f"https://api.github.com/repos/{self.repository}/releases/latest",
                headers={"Accept": "application/vnd.github+json", "User-Agent": "NovelCast"},
                timeout=3.0,
            )
            if response.status_code == 404:
                return None  # The repository has not published a release yet.
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Could not check GitHub releases for %s: %s", self.repository, exc)
            return None

        if not isinstance(payload, dict):
            return None

        latest_version = payload.get("tag_name")
        release_url = payload.get("html_url")
        current_key = _version_key(self.current_version)
        latest_key = _version_key(latest_version) if isinstance(latest_version, str) else None
        if not isinstance(release_url, str) or current_key is None or latest_key is None or latest_key <= current_key:
            return None

        return ReleaseUpdate(
            current_version=self.current_version,
            latest_version=latest_version,
            release_url=release_url,
        )
