import logging
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# -------------------------
# Helpers
# -------------------------

def wants_json(request: Request) -> bool:
    """
    Decide whether response should be JSON or HTML.
    JSON if:
    - API route
    - OR client explicitly asks for JSON
    """
    accept = request.headers.get("accept", "")
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
    """
    Safe HTML renderer with fallback in case templates are missing.
    This prevents crash-loops inside the error system.
    """

    templates: Jinja2Templates = getattr(
        request.app.state,
        "templates",
        None
    )

    # 🛡️ Fallback safety (VERY IMPORTANT)
    if not templates:
        logger.error("Templates not configured on app.state")
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": status_code,
                    "message": message,
                }
            },
        )

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


# -------------------------
# Exception Handlers
# -------------------------

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handles all HTTPExceptions raised intentionally in the app.
    """

    message = exc.detail if exc.detail else "HTTP Error"

    if wants_json(request):
        return render_json_error(exc.status_code, message)

    return render_html_error(request, exc.status_code, message)


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Handles all unexpected crashes.
    """

    logger.exception("Unhandled exception occurred", exc_info=exc)

    if wants_json(request):
        return render_json_error(500, "Internal Server Error")

    return render_html_error(request, 500, "Internal Server Error")


# -------------------------
# Registration
# -------------------------

def register_error_handlers(app: FastAPI):
    """
    Attach global exception handlers to FastAPI app.
    """

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)