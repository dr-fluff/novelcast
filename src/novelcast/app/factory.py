# novelcast/app/factory.py

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from novelcast.core.config import AppConfig
from novelcast.core.logging import setup_logging

from novelcast.api.errors import register_error_handlers
from novelcast.api.middleware import AuthMiddleware, PermissionMiddleware

from novelcast.auth.routes import router as auth_router

from novelcast.api.routes import pages
from novelcast.api.routes import users
from novelcast.api.routes import files
from novelcast.api.routes import admin
from novelcast.api.routes import download
from novelcast.api.routes import api as api_module

from novelcast.app.lifespan import lifespan

from novelcast.api.ws.notifications import router as ws_router

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(
        title="NovelCast",
        lifespan=lifespan,
    )

    # ─────────────────────────────
    # CORE SETUP
    # ─────────────────────────────
    setup_logging(config)

    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.config = config

    register_error_handlers(app)

    # ─────────────────────────────
    # MIDDLEWARE
    # ─────────────────────────────
    app.add_middleware(AuthMiddleware)
    app.add_middleware(PermissionMiddleware)

    # ─────────────────────────────
    # ROUTES
    # ─────────────────────────────

    # Auth routes should be available at root paths like /login /signup /logout
    app.include_router(auth_router)

    # Pages (UI routes)
    app.include_router(pages.router)

    # Feature APIs (non-core grouping)
    app.include_router(users.router, prefix="/users")
    app.include_router(files.router, prefix="/files")
    app.include_router(admin.router, prefix="/admin")

    # MAIN API ENTRYPOINT (IMPORTANT)
    # Everything under /api/* comes from api_module.router
    app.include_router(api_module.router, prefix="/api")

    # Legacy or direct POST support for download route
    app.post("/download/story")(download.add_story)

    app.include_router(ws_router)
    
    # ─────────────────────────────
    # STATIC FILES
    # ─────────────────────────────
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app