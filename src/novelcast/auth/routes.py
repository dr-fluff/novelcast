# novelcast/auth/routes.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from .session import create_session_token

router = APIRouter()


def qm(request: Request):
    return request.app.state.qm


def templates(request: Request):
    return request.app.state.templates


@router.get("/login")
def login_page(request: Request):
    return templates(request).TemplateResponse(
        "pages/login.html",
        {"request": request}
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = qm(request).fetchone(
        "users.get_by_username",
        (username,)
    )

    if not user or user["password"] != password:
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