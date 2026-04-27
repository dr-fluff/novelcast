# novelcast/api/errors.py
import logging
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    return (
        "application/json" in accept
        or request.url.path.startswith("/api")
    )


def render_json_error(status_code: int, message: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": status_code,
                "message": message,
            }
        },
    )


def render_html_error(request: Request, status_code: int, message: str):
    templates: Jinja2Templates = getattr(
        request.app.state,
        "templates",
        None
    )

    if not templates:
        logger.error(
            "Templates not configured",
            extra={
                "extra_data": {
                    "path": request.url.path,
                    "method": request.method,
                }
            },
        )
        return render_json_error(status_code, message)

    return templates.TemplateResponse(
        "pages/error.html",
        {
            "request": request,
            "error_code": status_code,
            "error_message": message,
            "path": request.url.path,
        },
        status_code=status_code,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail or "HTTP Error"

    logger.warning(
        "HTTP exception",
        extra={
            "extra_data": {
                "status_code": exc.status_code,
                "message": message,
                "path": request.url.path,
                "method": request.method,
            }
        },
    )

    if wants_json(request):
        return render_json_error(exc.status_code, message)

    return render_html_error(request, exc.status_code, message)


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception occurred",
        extra={
            "extra_data": {
                "path": request.url.path,
                "method": request.method,
            }
        },
    )

    if wants_json(request):
        return render_json_error(500, "Internal Server Error")

    return render_html_error(request, 500, "Internal Server Error")


def register_error_handlers(app: FastAPI):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)