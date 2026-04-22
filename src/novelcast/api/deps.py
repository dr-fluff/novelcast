from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService
from novelcast.core.config import AppConfig

from fastapi import Request, HTTPException


def get_user_service(request: Request) -> UserService:
    return request.app.state.users


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth


def get_context(request: Request):
    return request.app.state.ctx

def get_config(request: Request) -> AppConfig:
    return request.app.state.configs


def require_user(request: Request):
    if not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return request.state.user