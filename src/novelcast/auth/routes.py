# novelcast/auth/routes.py

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .session import create_session_token

router = APIRouter()


def templates(request: Request):
    return request.app.state.templates


# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@router.get("/login")
def login_page(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse("/", status_code=303)

    return templates(request).TemplateResponse(
        "pages/login.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    auth_service = request.app.state.auth
    user = auth_service.authenticate(username.strip(), password)

    if not user:
        return RedirectResponse("/login?error=invalid", status_code=303)

    token = create_session_token(user["id"])

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


# ─────────────────────────────
# SIGNUP
# ─────────────────────────────
@router.get("/signup")
def signup_page(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse("/", status_code=303)

    return templates(request).TemplateResponse(
        "pages/user_form.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
            "mode": "signup",
            "form_action": "/signup",
            "submit_label": "Create account",
            "back_url": "/login",
            "back_label": "← Back to login",
            "show_role": False,
            "form_user": None,
        },
    )


@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    username = username.strip()

    if not username or password != password_confirm:
        return RedirectResponse("/signup?error=invalid", status_code=303)

    user_service = request.app.state.users
    config_service = getattr(request.app.state, "settings", None)

    if user_service.get_user(username):
        return RedirectResponse("/signup?error=exists", status_code=303)

    user_count = user_service.count_users()
    accept_signup = True

    if config_service:
        raw = config_service.get_server_setting("users.accept_signup")
        if raw is not None:
            accept_signup = raw == "1"

    is_first_user = user_count == 0

    if not accept_signup and not is_first_user:
        return RedirectResponse("/signup?error=closed", status_code=303)

    user_service.create_user(username, password, is_root=is_first_user)

    return RedirectResponse("/login?success=created", status_code=303)


# ─────────────────────────────
# LOGOUT
# ─────────────────────────────
@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response


# ─────────────────────────────
# FORGOT PASSWORD
# ─────────────────────────────
@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates(request).TemplateResponse(
        "pages/forgot_password.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
            "success": request.query_params.get("success"),
        },
    )


@router.post("/forgot-password")
def forgot_password_submit(request: Request, username: str = Form(...)):
    password_reset = request.app.state.password_reset  # ✅ FIXED (no ctx)

    token = password_reset.request_reset(username.strip())

    if token:
        print(f"[RESET LINK] http://localhost:8001/reset-password?token={token}")

    return RedirectResponse("/login?success=reset-sent", status_code=303)


# ─────────────────────────────
# RESET PASSWORD
# ─────────────────────────────
@router.get("/reset-password")
def reset_password_page(request: Request, token: str):
    return templates(request).TemplateResponse(
        "pages/reset_password.html",
        {
            "request": request,
            "token": token,
            "error": request.query_params.get("error"),
        },
    )


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    if password != password_confirm:
        return RedirectResponse(
            f"/reset-password?token={token}&error=match",
            status_code=303,
        )

    password_reset = request.app.state.password_reset  # ✅ FIXED

    ok = password_reset.reset_password(token, password)

    if not ok:
        return RedirectResponse("/forgot-password?error=invalid", status_code=303)

    return RedirectResponse("/login?success=reset", status_code=303)
