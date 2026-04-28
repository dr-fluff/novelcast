import uuid
import logging
from http.cookies import SimpleCookie

from fastapi.responses import RedirectResponse, JSONResponse
from novelcast.auth.session import decode_session_token
from novelcast.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

class DebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        print("➡️ ENTER REQUEST", scope["path"])

        async def wrapped_receive():
            message = await receive()
            print("📥 RECEIVE:", message["type"])
            return message

        await self.app(scope, wrapped_receive, send)

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])

        request_id = headers.get(b"x-request-id")
        if request_id:
            request_id = request_id.decode()
        else:
            request_id = str(uuid.uuid4())

        token = request_id_ctx.set(request_id)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_ctx.reset(token)


class AuthMiddleware:
    PUBLIC_PATHS = {"/login", "/signup", "/logout", "/favicon.ico"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])
        cookie_header = headers.get(b"cookie", b"").decode()
        cookie = SimpleCookie()
        cookie.load(cookie_header)

        user = None
        session_token = cookie.get("session").value if "session" in cookie else None
        user_id = decode_session_token(session_token) if session_token else None

        if user_id:
            try:
                auth_service = scope["app"].state.auth
                user = auth_service.get_user_by_id(user_id)
            except Exception:
                logger.exception(
                    "Unexpected error during authentication",
                    extra={"extra_data": {"user_id": user_id}},
                )
                return await self._json_500(send)

        scope.setdefault("state", {})
        scope["state"]["user"] = user

        path = scope.get("path", "")
        if user and path in self.PUBLIC_PATHS:
            response = RedirectResponse("/", status_code=303)
            return await response(scope, receive, send)

        if not user and not path.startswith("/static") and path not in self.PUBLIC_PATHS:
            response = RedirectResponse("/login", status_code=303)
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)

    async def _json_500(self, send):
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"detail":"Authentication service error"}',
        })


class PermissionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        state = scope.get("state", {})
        user = state.get("user")

        if user and hasattr(user, "is_active") and not user.is_active:
            response = JSONResponse(
                status_code=403,
                content={"detail": "User is inactive"},
            )
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)