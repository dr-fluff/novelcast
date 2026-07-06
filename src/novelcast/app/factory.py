# novelcast/app/factory.py

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from novelcast import app
from novelcast.core.config import AppConfig

from novelcast.api.errors import register_error_handlers
from novelcast.api import (
    RequestIDMiddleware,
    AuthMiddleware,
    PermissionMiddleware,
)

from novelcast.app.lifespan import lifespan
from novelcast.core.templates import AppTemplates
from novelcast.api.routes import router as api_router
from novelcast.core.logging import setup_logging, LogConfig



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

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )
    
    return app