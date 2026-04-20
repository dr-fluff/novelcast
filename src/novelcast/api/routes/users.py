from fastapi import APIRouter
from fastapi import Request

from novelcast.core.context import AppContext
from novelcast.services.auth_service import AuthService

router = APIRouter()
service = AuthService(AppContext().qm)

def get_router():
    return router


def get_auth(request: Request):
    return request.app.state.auth

@router.post("/create")
def create_user(username: str, password_hash: str):
    service.create_user(username, password_hash)
    return {"status": "created"}


@router.get("/{username}")
def get_user(username: str):
    return service.get_user(username)