# /novelcast/api/routers/utils.py
from fastapi import Depends, HTTPException

from novelcast.api.deps import get_current_user


def require_admin(current_user: dict | None = Depends(get_current_user)) -> dict:
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
