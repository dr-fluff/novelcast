# novelcast/api/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from novelcast.api.deps import get_current_user, get_users
from novelcast.services import UserService

router = APIRouter(prefix="/users", tags=["admin"])


@router.post("/{user_id}/promote")
def promote_user(
    user_id: int,
    current_user: dict | None = Depends(get_current_user),
    users: UserService = Depends(get_users),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")

    users.promote_to_admin(user_id)
    return RedirectResponse("/settings?success=1", status_code=303)