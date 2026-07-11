import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as HTTPException

logger = logging.getLogger(__name__)


# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()

    return "application/json" in accept or request.url.path.startswith("/api")


def error_response(
    request: Request,
    status_code: int,
    message: str,
) -> Response:
    """
    Return either JSON or HTML error response
    based on request expectations.
    """

    if wants_json(request):
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": status_code,
                    "message": message,
                }
            },
        )

    templates: Jinja2Templates | None = getattr(
        request.app.state,
        "templates",
        None,
    )

    if not templates:
        logger.error("Templates not configured")

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


# ─────────────────────────────
# EXCEPTION HANDLERS
# ─────────────────────────────
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    message = exc.detail or "HTTP Error"

    logger.warning(
        "HTTP exception occurred",
        extra={
            "extra_data": {
                "status_code": exc.status_code,
                "message": message,
                "path": request.url.path,
                "method": request.method,
            }
        },
    )

    if exc.status_code in {401, 403} and not wants_json(request):
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    return error_response(
        request,
        exc.status_code,
        message,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled exception occurred",
        extra={
            "extra_data": {
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
            }
        },
    )

    return error_response(
        request,
        500,
        "Internal Server Error",
    )


# ─────────────────────────────
# REGISTER
# ─────────────────────────────
def register_error_handlers(app: FastAPI) -> None:
    app.exception_handler(HTTPException)(http_exception_handler)

    app.exception_handler(Exception)(unhandled_exception_handler)
