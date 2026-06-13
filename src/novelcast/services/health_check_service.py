from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

Status = Literal["healthy", "warning", "not_healthy", "not_configured"]


@dataclass
class HealthResult:
    name: str
    status: Status
    detail: str
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail, "meta": self.meta}


class HealthCheckService:
    DISK_WARNING_PCT  = 80
    DISK_CRITICAL_PCT = 90

    def __init__(
        self,
        session_factory: Callable[[], Session],
        stories_dir: str | None = None,
        worker_last_ping_ts: float | None = None,
    ):
        # Takes a factory (like SessionLocal) so it can open a fresh
        # session per check — same pattern as every other service in AppContext.
        self._session_factory = session_factory
        self._stories_dir = stories_dir
        self._worker_last_ping_ts = worker_last_ping_ts

    # ── Individual checks ───────────────────────────────────────────────────

    def check_database(self) -> HealthResult:
        try:
            db = self._session_factory()
            try:
                db.execute(text("SELECT 1"))
            finally:
                db.close()
            return HealthResult("Database", "healthy", "Connection successful")
        except Exception as exc:
            return HealthResult("Database", "not_healthy", str(exc))

    def check_disk(self) -> HealthResult:
        path = self._stories_dir or "/"
        try:
            usage   = shutil.disk_usage(path)
            pct     = int(usage.used / usage.total * 100)
            free_gb = round(usage.free / (1024 ** 3), 1)
            meta    = {"used_pct": pct, "free_gb": free_gb}
            label   = f"{pct}% used — {free_gb} GB free"
            if pct >= self.DISK_CRITICAL_PCT:
                return HealthResult("Disk Storage", "not_healthy", label, meta)
            if pct >= self.DISK_WARNING_PCT:
                return HealthResult("Disk Storage", "warning", label, meta)
            return HealthResult("Disk Storage", "healthy", label, meta)
        except FileNotFoundError:
            return HealthResult("Disk Storage", "not_configured", f"Path not found: {path}")
        except Exception as exc:
            return HealthResult("Disk Storage", "not_healthy", str(exc))

    def check_sync_worker(self) -> HealthResult:
        if self._worker_last_ping_ts is None:
            return HealthResult("Sync Worker", "not_configured", "Heartbeat not configured")
        age = time.time() - self._worker_last_ping_ts
        if age < 120:
            return HealthResult("Sync Worker", "healthy",     f"Active (last ping {int(age)}s ago)",      {"last_ping_age_s": int(age)})
        if age < 600:
            return HealthResult("Sync Worker", "warning",     f"Slow — last ping {int(age // 60)}m ago", {"last_ping_age_s": int(age)})
        return     HealthResult("Sync Worker", "not_healthy", f"No response — {int(age // 60)}m ago",    {"last_ping_age_s": int(age)})

    def check_pending_syncs(self, pending: int) -> HealthResult:
        meta = {"count": pending}
        if pending == 0:
            return HealthResult("Pending Syncs", "healthy",     "All stories up to date", meta)
        if pending < 10:
            return HealthResult("Pending Syncs", "warning",     f"{pending} stor{'y' if pending == 1 else 'ies'} need syncing", meta)
        return     HealthResult("Pending Syncs", "not_healthy", f"{pending} stories need syncing", meta)

    # ── Run all ─────────────────────────────────────────────────────────────

    def run_all(self, pending_syncs: int = 0) -> list[HealthResult]:
        return [
            self.check_database(),
            self.check_disk(),
            self.check_sync_worker(),
            self.check_pending_syncs(pending_syncs),
        ]