from fastapi import APIRouter, Depends
 
from novelcast.api.deps import get_users, get_auth
from novelcast.services import UserService
from novelcast.services import AuthService
 
router = APIRouter(prefix="/users", tags=["users"])
 
 
@router.post("/create")
def create_user(
    username: str,
    password: str,
    users: UserService = Depends(get_users),
):
    users.create_user(username, password)
    return {"status": "created"}
 
 
@router.get("/{username}")
def get_user(
    username: str,
    users: UserService = Depends(get_users),
):
    return users.get_user(username)
 