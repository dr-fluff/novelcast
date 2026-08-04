# novelcast/api/routes/pages/account.py

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from novelcast.api.deps import get_auth, get_current_user, get_templates, get_users
from novelcast.services import AuthService, UserService
from novelcast.utils.password_validation import validate_password_strength

router = APIRouter()


@router.get("/account/password")
def change_password_page(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        "pages/change_password.html",
        {
            "request": request,
            "current_user": current_user,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/account/password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    auth: AuthService = Depends(get_auth),
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    # Re-authenticate with the current password before allowing a change —
    # same check the login route uses, so a hijacked-but-unlocked session
    # (or someone at a shared computer) can't silently take over the account.
    if not auth.authenticate(current_user["username"], current_password):
        return RedirectResponse("/account/password?error=wrong_current", status_code=303)

    if new_password != new_password_confirm:
        return RedirectResponse("/account/password?error=match", status_code=303)

    password_errors = validate_password_strength(new_password)
    if password_errors:
        return RedirectResponse("/account/password?error=weak_password", status_code=303)

    users.update_user(
        current_user["id"],
        username=current_user["username"],
        password=new_password,
        is_root=current_user.get("is_root", False),
    )

    return RedirectResponse("/account/password?success=1", status_code=303)


class VerifyPasswordRequest(BaseModel):
    current_password: str


@router.post("/account/verify-password")
def verify_current_password(
    payload: VerifyPasswordRequest,
    auth: AuthService = Depends(get_auth),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user:
        return JSONResponse({"valid": False}, status_code=401)

    valid = bool(auth.authenticate(current_user["username"], payload.current_password))
    return {"valid": valid}
