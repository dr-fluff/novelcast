# api/routes/admin.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()


def qm(request: Request):
    return request.app.state.qm


# ─────────────────────────────
# Admin actions
# ─────────────────────────────
@router.post("/users/{user_id}/promote")
def promote_user(request: Request, user_id: int):
    user = getattr(request.state, "user", None)
    if not user or not user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")

    request.app.state.users.promote_to_admin(user_id)
    return RedirectResponse("/settings?success=1", status_code=303)
