from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        username = request.headers.get("x-user")

        if username:
            request.state.user = request.app.state.users.get_user(username)
        else:
            request.state.user = None

        return await call_next(request)


class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if request.url.path.startswith("/static"):
            return await call_next(request)

        if request.url.path.startswith("/api"):
            if not getattr(request.state, "user", None):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)

        if not getattr(request.state, "user", None):
            return RedirectResponse("/login")

        return await call_next(request)