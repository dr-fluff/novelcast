# /novelcast/api/router/__init__.py
from fastapi import APIRouter

from novelcast.auth.routes import router as auth_router
from .pages import router as pages_router
from .admin import router as admin_router
from .admin.telegram import router as telegram_router
from . import static, users, files, stories, download, sync, password_reset

router = APIRouter()

# ── HTML pages ────────────────────────────────────────────────────────────
router.include_router(auth_router)
router.include_router(pages_router)
router.include_router(password_reset.router)

# ── Static assets ─────────────────────────────────────────────────────────
router.include_router(static.router)

# ── JSON APIs (all under /api) ────────────────────────────────────────────
api_router = APIRouter(prefix="/api")
api_router.include_router(users.router,    prefix="/users",    tags=["users"])
api_router.include_router(files.router,    prefix="/files",    tags=["files"])
api_router.include_router(stories.router,  prefix="/stories",  tags=["stories"])
api_router.include_router(download.router, prefix="/download", tags=["download"])
api_router.include_router(sync.router,     prefix="/sync",     tags=["sync"])

# ── Admin APIs ────────────────────────────────────────────────────────────
api_router.include_router(admin_router,    prefix="/admin",    tags=["admin"])
api_router.include_router(telegram_router, prefix="/admin/telegram", tags=["admin"])

router.include_router(api_router)