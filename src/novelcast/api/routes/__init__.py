# /novelcast/api/router/__init__.py
from fastapi import APIRouter

from novelcast.api.ws.notifications import router as notifications_router
from novelcast.auth.routes import router as auth_router

from . import add_story, download, files, password_reset, static, stories, sync, users
from .admin import router as admin_router
from .pages import router as pages_router

router = APIRouter()

# ── HTML pages ────────────────────────────────────────────────────────────
router.include_router(auth_router)
router.include_router(pages_router)
router.include_router(password_reset.router)


# ── Static assets ─────────────────────────────────────────────────────────
router.include_router(static.router)
router.include_router(notifications_router)


# ── JSON APIs (all under /api) ────────────────────────────────────────────
api_router = APIRouter(prefix="/api")
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(add_story.router, prefix="/stories", tags=["stories"])
api_router.include_router(download.router, prefix="/download", tags=["download"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])

# ── Admin APIs ────────────────────────────────────────────────────────────
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

router.include_router(api_router)
