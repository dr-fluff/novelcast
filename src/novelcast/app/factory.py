# novelcast/app/factory.py

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from novelcast.api import (
    AuthMiddleware,
    PermissionMiddleware,
    RequestIDMiddleware,
)
from novelcast.api.errors import register_error_handlers
from novelcast.api.routes import router as api_router
from novelcast.app.lifespan import lifespan
from novelcast.core.config import AppConfig
from novelcast.core.logging import LogConfig, setup_logging
from novelcast.core.templates import AppTemplates

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(config: AppConfig) -> FastAPI:
    setup_logging(LogConfig.console_only())

    app = FastAPI(
        title="NovelCast",
        lifespan=lifespan,
    )

    register_error_handlers(app)

    app.state.config = config
    app.state.templates = AppTemplates(directory=str(TEMPLATES_DIR))
    app.state.templates = AppTemplates(directory=str(TEMPLATES_DIR))
    app.state.templates.env.globals["api_port"] = config.port

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(PermissionMiddleware)

    app.include_router(api_router)

    # Served at the origin root (not under /static) so its default max
    # scope is "/" -- a service worker's scope can never extend above the
    # path it's served from, and the /static mount would otherwise cap it
    # at /static/*, which excludes every real app page (/, /story, /chapter).
    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():
        return FileResponse(
            STATIC_DIR / "sw.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    return app
