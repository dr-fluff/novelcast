# novelcast/api/routers/users.py
from fastapi import APIRouter, Depends, HTTPException

from novelcast.api.deps import get_users
from novelcast.services import UserService
from novelcast.utils.password_validation import validate_password_strength

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/create")
def create_user(
    username: str,
    password: str,
    users: UserService = Depends(get_users),
):
    password_errors = validate_password_strength(password)
    if password_errors:
        raise HTTPException(status_code=400, detail={"errors": password_errors})

    users.create_user(username, password)
    return {"status": "created"}


@router.get("/{username}")
def get_user(
    username: str,
    users: UserService = Depends(get_users),
):
    return users.get_user(username)
