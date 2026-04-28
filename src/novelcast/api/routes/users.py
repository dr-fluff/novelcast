# api/routes/users.py

from fastapi import APIRouter, Request
from novelcast.services.auth_service import AuthService
from novelcast.services.user_service import UserService

router = APIRouter()


def users(request: Request) -> UserService:
    return request.app.state.users


def auth(request: Request) -> AuthService:
    return request.app.state.auth


# ─────────────────────────────
# Create user
# ─────────────────────────────
@router.post("/create")
def create_user(request: Request, username: str, password: str):
    users(request).create_user(username, password)
    return {"status": "created"}


# ─────────────────────────────
# Get user
# ─────────────────────────────
@router.get("/{username}")
def get_user(request: Request, username: str):
    return users(request).get_user(username)