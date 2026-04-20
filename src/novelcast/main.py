from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from novelcast.core.context import AppContext
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService

from novelcast.api.middleware import PermissionMiddleware, AuthMiddleware
from novelcast.api.routes.users import router as users_router
from novelcast.api.routes.files import router as files_router
from novelcast.api.routes.admin import router as admin_router


# ─────────────────────────────
# PATHS
# ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = Path("data/novelcast.db")


# ─────────────────────────────
# LIFESPAN
# ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppContext()
    ctx.init()

    user_service = UserService(ctx.qm)
    auth_service = AuthService(user_service)

    app.state.ctx = ctx
    app.state.users = user_service
    app.state.auth = auth_service
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    yield

    ctx.db.close()


# ─────────────────────────────
# APP
# ─────────────────────────────
app = FastAPI(title="NovelCast", lifespan=lifespan)


# ─────────────────────────────
# MIDDLEWARE (ORDER MATTERS)
# ─────────────────────────────
app.add_middleware(AuthMiddleware)
app.add_middleware(PermissionMiddleware)


# ─────────────────────────────
# ROUTES
# ─────────────────────────────
app.include_router(users_router, prefix="/users")
app.include_router(files_router, prefix="/files")
app.include_router(admin_router, prefix="/admin")


# ─────────────────────────────
# STATIC
# ─────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─────────────────────────────
# HTML ERROR HANDLER
# ─────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    templates = request.app.state.templates

    return templates.TemplateResponse(
        "pages/error.html",
        {
            "request": request,
            "error_code": exc.status_code,
            "error_message": exc.detail,
            "path": request.url.path,
        },
        status_code=exc.status_code,
    )


# ─────────────────────────────
# 500 HANDLER (IMPORTANT)
# ─────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    templates = request.app.state.templates

    return templates.TemplateResponse(
        "pages/error.html",
        {
            "request": request,
            "error_code": 500,
            "error_message": str(exc),
            "path": request.url.path,
        },
        status_code=500,
    )