# novelcast/auth/routes.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from .session import create_session_token

router = APIRouter()


def templates(request: Request):
    return request.app.state.templates


@router.get("/login")
def login_page(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse("/", status_code=303)

    error = request.query_params.get("error")
    success = request.query_params.get("success")
    return templates(request).TemplateResponse(
        "pages/login.html",
        {"request": request, "error": error, "success": success},
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
        samesite="lax"
    )
    return response


@router.get("/signup")
def signup_page(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse("/", status_code=303)

    error = request.query_params.get("error")
    return templates(request).TemplateResponse(
        "pages/signup.html",
        {"request": request, "error": error},
    )


@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    username = username.strip()
    if not username or not password or password != password_confirm:
        return RedirectResponse("/signup?error=invalid", status_code=303)

    user_service = request.app.state.users
    existing = user_service.get_user(username)
    if existing:
        return RedirectResponse("/signup?error=exists", status_code=303)

    user_service.create_user(username, password)
    return RedirectResponse("/login?success=created", status_code=303)


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response