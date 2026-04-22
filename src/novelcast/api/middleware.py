from os import path
from urllib import request

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = request.headers.get("x-user")
        request.state.user = None

        if username:
            try:
                request.state.user = request.app.state.users.get_user(username)
            except Exception:
                request.state.user = None

        return await call_next(request)


class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = request.headers.get("x-user")

        request.state.user = None
        if username:
            request.state.user = request.app.state.users.get_user(username)

        return await call_next(request)