import uuid
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from novelcast.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


# -------------------------
# REQUEST ID MIDDLEWARE
# -------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

        token = request_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response

        finally:
            request_id_ctx.reset(token)


# -------------------------
# AUTH MIDDLEWARE
# -------------------------
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        username = request.headers.get("x-user")

        if username:
            try:
                user_service = request.app.state.users
                user = user_service.get_user(username)

                request.state.user = user

                if user is None:
                    logger.warning(
                        "User not found",
                        extra={
                            "extra_data": {
                                "username": username,
                            }
                        },
                    )

            except KeyError:
                logger.warning(
                    "User lookup failed (KeyError)",
                    extra={
                        "extra_data": {
                            "username": username,
                        }
                    },
                )

            except Exception:
                logger.exception(
                    "Unexpected error during authentication",
                    extra={
                        "extra_data": {
                            "username": username,
                        }
                    },
                )

                return JSONResponse(
                    status_code=500,
                    content={"detail": "Authentication service error"},
                )

        try:
            return await call_next(request)

        except Exception:
            logger.exception(
                "Unhandled error during request processing",
                extra={
                    "extra_data": {
                        "path": request.url.path,
                        "method": request.method,
                    }
                },
            )

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = getattr(request.state, "user", None)

        # safe now
        if user and hasattr(user, "is_active") and not user.is_active:
            return JSONResponse(
                status_code=403,
                content={"detail": "User is inactive"},
            )

        return await call_next(request)