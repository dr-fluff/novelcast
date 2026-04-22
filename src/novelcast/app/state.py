from fastapi import Request
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService


def get_user_service(request: Request) -> UserService:
    return request.app.state.users


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth


def get_context(request: Request):
    return request.app.state.ctx