from fastapi import APIRouter, Depends, Request

from novelcast.api.deps import get_current_user
from novelcast.api.routes import admin, download, files, pages, password_reset, stories, sync, users

router = APIRouter()

# ── Page routes (HTML) ──────────────────────────────────────────────────────
router.include_router(pages.router)
router.include_router(password_reset.router)

# ── API routes (JSON) ───────────────────────────────────────────────────────
router.include_router(users.router)
router.include_router(files.router)
router.include_router(download.router)
router.include_router(sync.router)
router.include_router(stories.router)
router.include_router(admin.router)


@router.get("/status")
def get_status(request: Request):
    return {
        "status": "ok",
        "db": "connected" if request.app.state.db else "missing",
    }
