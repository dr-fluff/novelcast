from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from novelcast.core.context import AppContext
from .session import create_session_token

router = APIRouter()
ctx = AppContext()


@router.get("/login")
def login_page(request: Request):
    return ctx.templates.TemplateResponse(
        "pages/login.html",
        {"request": request}
    )


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    user = ctx.qm.fetchone(
        "users.get_by_username",
        (username,)
    )

    if not user:
        return RedirectResponse("/login", status_code=303)

    # NOTE: replace with real password hashing check
    if user["password"] != password:
        return RedirectResponse("/login", status_code=303)

    token = create_session_token(user["id"])

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session")
    return response