from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from novelcast.core.config import AppConfig
from novelcast.core.context import AppContext
from novelcast.core.logging import setup_logging
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService

from novelcast.api.routes import download

from novelcast.api.errors import register_error_handlers
from novelcast.api.middleware import AuthMiddleware, PermissionMiddleware

from novelcast.app.lifespan import lifespan


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(
        title="NovelCast",
        lifespan=lifespan,
    )
    setup_logging(config) 

    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    register_error_handlers(app)

    app.add_middleware(AuthMiddleware)
    app.add_middleware(PermissionMiddleware)

    from novelcast.api.routes.pages import router as pages_router
    from novelcast.api.routes.users import router as users_router
    from novelcast.api.routes.files import router as files_router
    from novelcast.api.routes.admin import router as admin_router
    from novelcast.api.routes.api import router as api_router

    app.include_router(pages_router)
    app.include_router(users_router, prefix="/users")
    app.include_router(files_router, prefix="/files")
    app.include_router(admin_router, prefix="/admin")
    app.include_router(api_router, prefix="/api")
    
    app.include_router(download.router)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app