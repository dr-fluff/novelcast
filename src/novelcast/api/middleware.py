# novelcast/api/middleware.py

import logging
import uuid
from http.cookies import SimpleCookie

from starlette.responses import JSONResponse, RedirectResponse

from novelcast.auth.session import decode_session_token
from novelcast.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


# ─────────────────────────────
# REQUEST ID MIDDLEWARE
# ─────────────────────────────
class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", []))

        request_id = headers.get(b"x-request-id")
        request_id = request_id.decode() if request_id else str(uuid.uuid4())

        token = request_id_ctx.set(request_id)

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            return await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)


# ─────────────────────────────
# AUTH MIDDLEWARE
# ─────────────────────────────
class AuthMiddleware:
    PUBLIC_PATHS = {
        "/login",
        "/signup",
        "/logout",
        "/forgot-password",
        "/reset-password",
        "/favicon.svg",
    }

    # paths that stay accessible even if the user is logged in
    ALWAYS_ACCESSIBLE = {"/logout"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"").decode()

        cookie = SimpleCookie()
        cookie.load(cookie_header)

        session_cookie = cookie.get("session")
        session_token = session_cookie.value if session_cookie else None

        user = None

        try:
            if session_token:
                user_id = decode_session_token(session_token)
                if user_id:
                    auth_service = scope["app"].state.auth
                    user = auth_service.get_user_by_id(user_id)

        except Exception:
            logger.exception("Auth error during session validation")

            response = JSONResponse(
                status_code=500,
                content={"detail": "Authentication service error"},
            )
            return await response(scope, receive, send)

        state = scope.setdefault("state", {})
        state["user"] = user

        # logged-in users should not see auth pages (except logout)
        if user and path in self.PUBLIC_PATHS and path not in self.ALWAYS_ACCESSIBLE:
            response = RedirectResponse("/", status_code=303)
            return await response(scope, receive, send)

        # protect private routes
        if (
            not user
            and path not in self.PUBLIC_PATHS
            and not path.startswith("/static")
            and not path.startswith("/api")
            and not path.startswith("/ws")
        ):
            response = RedirectResponse("/login", status_code=303)
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)


# ─────────────────────────────
# PERMISSION MIDDLEWARE
# ─────────────────────────────
class PermissionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        state = scope.get("state", {})
        user = state.get("user")

        if user and user.get("is_active") is False:
            response = JSONResponse(
                status_code=403,
                content={"detail": "User is inactive"},
            )
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)
