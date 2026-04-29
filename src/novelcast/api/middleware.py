# api/middleware.py

import uuid
import logging
import traceback
from http.cookies import SimpleCookie

from fastapi.responses import RedirectResponse, JSONResponse

from novelcast.auth.session import decode_session_token
from novelcast.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

class DebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        logger.debug("➡️ ENTER REQUEST %s", scope.get("path"))

        async def wrapped_receive():
            message = await receive()
            logger.debug("📥 RECEIVE: %s", message.get("type"))
            return message

        return await self.app(scope, wrapped_receive, send)


class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])

        request_id = headers.get(b"x-request-id")
        request_id = request_id.decode() if request_id else str(uuid.uuid4())

        token = request_id_ctx.set(request_id)

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            return await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)


class ExceptionMiddleware:
    def __init__(self, app, debug: bool = False):
        self.app = app
        self.debug = debug

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        try:
            return await self.app(scope, receive, send)

        except Exception as exc:
            request_id = None

            try:
                headers = dict(scope.get("headers", []))
                request_id = headers.get(b"x-request-id", b"").decode()
            except Exception:
                pass

            logger.exception(
                "Unhandled exception in request pipeline",
                extra={
                    "request_id": request_id,
                    "path": scope.get("path"),
                },
            )

            body = {"detail": "Internal Server Error"}

            if self.debug:
                body["error"] = str(exc)
                body["trace"] = traceback.format_exc()

            response = JSONResponse(status_code=500, content=body)
            return await response(scope, receive, send)


class AuthMiddleware:
    PUBLIC_PATHS = {"/login", "/signup", "/logout", "/favicon.ico"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        headers = dict(scope["headers"])
        cookie_header = headers.get(b"cookie", b"").decode()

        cookie = SimpleCookie()
        cookie.load(cookie_header)

        session_token = cookie.get("session").value if "session" in cookie else None

        user = None

        try:
            if session_token:
                user_id = decode_session_token(session_token)
                if user_id:
                    auth_service = scope["app"].state.auth
                    user = auth_service.get_user_by_id(user_id)

        except Exception:
            logger.exception(
                "Authentication error during session validation",
                extra={"path": path},
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication service error"},
            )

        scope.setdefault("state", {})
        scope["state"]["user"] = user

        # Redirect authenticated users away from auth pages
        if user and path in self.PUBLIC_PATHS:
            return RedirectResponse("/", status_code=303)

        # Redirect unauthenticated users to login
        if (
            not user
            and path not in self.PUBLIC_PATHS
            and not path.startswith("/static")
        ):
            return RedirectResponse("/login", status_code=303)

        return await self.app(scope, receive, send)

class PermissionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        user = scope.get("state", {}).get("user")

        if user and getattr(user, "is_active", True) is False:
            response = JSONResponse(
                status_code=403,
                content={"detail": "User is inactive"},
            )
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)