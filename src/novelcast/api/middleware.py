import uuid
import logging

from starlette.responses import JSONResponse
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
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])
        username = headers.get(b"x-user")
        user = None

        if username:
            try:
                username = username.decode()
                user_service = scope["app"].state.users
                user = user_service.get_user(username)

                if user is None:
                    logger.warning(
                        "User not found",
                        extra={"extra_data": {"username": username}},
                    )

            except KeyError:
                logger.warning(
                    "User lookup failed (KeyError)",
                    extra={"extra_data": {"username": username.decode() if username else None}},
                )

            except Exception:
                logger.exception(
                    "Unexpected error during authentication",
                    extra={"extra_data": {"username": username.decode() if username else None}},
                )
                return await self._json_500(send)

        scope.setdefault("state", {})
        scope["state"]["user"] = user

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