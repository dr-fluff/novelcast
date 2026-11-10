# novelcast/api/router/admin/__init__.py
import subprocess
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from novelcast.api.deps import (
    get_chapter_filter,
    get_current_user,
    get_health_check,
    get_library_sync,
    get_users,
)
from novelcast.api.routes.utils import require_admin
from novelcast.services import HealthCheckService, LibrarySyncService, UserService
from novelcast.services.chapter_filter_service import ChapterFilterService

from .log_tail import router as log_tail_router
from .patreon import router as patreon_router
from .telegram import router as telegram_router

router = APIRouter()

router.include_router(telegram_router, prefix="/telegram")
router.include_router(patreon_router, prefix="/patreon")
router.include_router(log_tail_router, prefix="/logs", tags=["admin"])


def _has_tracked_local_changes(repo_dir: Path) -> bool:
    commands = (
        ["git", "diff", "--quiet", "--", ".", ":(exclude)scripts/update.sh"],
        ["git", "diff", "--cached", "--quiet"],
    )
    for command in commands:
        result = subprocess.run(
            command,
            cwd=repo_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode == 1:
            return True
        if result.returncode != 0:
            raise RuntimeError("Could not check the repository for local changes.")
    return False


@router.post("/update", response_class=HTMLResponse)
def install_latest_release(request: Request, _admin: dict = Depends(require_admin)):
    release_updates = request.app.state.release_updates
    release = release_updates.get_available_update(refresh=True)
    if release is None:
        return HTMLResponse("<span>No newer GitHub release is available.</span>")

    repo_dir = Path(__file__).resolve().parents[5]
    if Path("/.dockerenv").exists() or not (repo_dir / ".git").exists():
        return HTMLResponse(
            "<span>Docker updates must be run on the host: "
            "<code>git pull --ff-only</code>, then <code>docker compose up -d --build</code>.</span>"
        )

    update_script = repo_dir / "scripts" / "update.sh"
    if not update_script.is_file():
        return HTMLResponse("<span>The managed update script was not found.</span>")

    try:
        if _has_tracked_local_changes(repo_dir):
            return HTMLResponse(
                "<span>ERROR: Other tracked files have local changes. "
                "Commit or stash those changes before updating.</span>"
            )
    except (OSError, RuntimeError):
        return HTMLResponse("<span>Could not check for local changes before updating.</span>")

    command = [
        "systemd-run",
        "--system",
        "--no-block",
        "--collect",
        "--unit=novelcast-update.service",
        f"--property=WorkingDirectory={repo_dir}",
        "/bin/bash",
        str(update_script),
        release.latest_version,
        release_updates.repository,
    ]

    try:
        result = subprocess.run(
            command,
            cwd=repo_dir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError:
        return HTMLResponse(
            "<span>Could not launch the systemd update job. "
            "Check NovelCast service logs.</span>"
        )

    if result.returncode != 0:
        detail = (result.stdout or "").strip()
        return HTMLResponse(
            "<span>Could not start the update job. "
            f"<code>{escape(detail)}</code></span>"
        )

    return HTMLResponse(
        f"<span>Updating to NovelCast {release.latest_version}. "
        "The app will restart when installation is complete. "
        "Update output is available through journalctl.</span>"
    )


# ── Users ─────────────────────────────────────────────────────────────────


@router.post("/users/{user_id}/promote")
def promote_user(
    user_id: int,
    current_user: dict | None = Depends(get_current_user),
    users: UserService = Depends(get_users),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")
    users.promote_to_admin(user_id)
    return RedirectResponse("/settings?success=1", status_code=303)


@router.post("/users/{user_id}/edit")
def edit_user(
    request: Request,
    user_id: int,
    username: str = Form(...),
    password: str | None = Form(None),
    password_confirm: str | None = Form(None),
    role: str = Form("user"),
    current_user: dict = Depends(require_admin),
    users: UserService = Depends(get_users),
):
    if current_user.get("id") == user_id and role != "admin":
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=demote", status_code=303)
    if role not in {"user", "admin"}:
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=invalid", status_code=303)
    if password and password != password_confirm:
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=invalid", status_code=303)

    try:
        updated = users.update_user(user_id, username=username, password=password, is_root=(role == "admin"))
    except ValueError:
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=invalid", status_code=303)
    except IntegrityError:
        return RedirectResponse(f"/admin/users/{user_id}/edit?error=exists", status_code=303)

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse("/admin/users?success=1", status_code=303)


# ── Chapter patterns ──────────────────────────────────────────────────────


class PatternCreate(BaseModel):
    pattern: str
    description: str = ""


class PatternPatch(BaseModel):
    enabled: bool | None = None
    pattern: str | None = None
    description: str | None = None


class PatternTest(BaseModel):
    pattern: str
    samples: list[str]


@router.get("/chapter-patterns")
def list_patterns(
    _user: dict = Depends(require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    return svc.get_all_patterns()


@router.post("/chapter-patterns", status_code=201)
def create_pattern(
    body: PatternCreate,
    _user: dict = Depends(require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    try:
        return svc.add_pattern(body.pattern, body.description)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.patch("/chapter-patterns/{pattern_id}")
def patch_pattern(
    pattern_id: int,
    body: PatternPatch,
    _user: dict = Depends(require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    if body.enabled is not None:
        svc.set_enabled(pattern_id, body.enabled)
    if body.pattern is not None or body.description is not None:
        existing = svc.get_all_patterns()
        row = next((p for p in existing if p["id"] == pattern_id), None)
        if not row:
            raise HTTPException(status_code=404, detail="Pattern not found")
        try:
            svc.update_pattern(
                pattern_id,
                body.pattern or row["pattern"],
                body.description if body.description is not None else row["description"],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
    return {"ok": True}


@router.delete("/chapter-patterns/{pattern_id}", status_code=204)
def delete_pattern(
    pattern_id: int,
    _user: dict = Depends(require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    svc.delete_pattern(pattern_id)


@router.post("/chapter-patterns/test")
def test_pattern(
    body: PatternTest,
    _user: dict = Depends(require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    try:
        return svc.test_pattern(body.pattern, body.samples)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# ── Health ────────────────────────────────────────────────────────────────


@router.get("/health")
def health_check(
    _user: dict = Depends(require_admin),
    svc: HealthCheckService = Depends(get_health_check),
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    pending = library_sync.pending_count()
    return [r.as_dict() for r in svc.run_all(pending_syncs=pending)]
