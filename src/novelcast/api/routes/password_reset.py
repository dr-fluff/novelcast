from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

router = APIRouter()


def service(request: Request):
    return request.app.state.ctx.password_reset


@router.get("/forgot-password")
def forgot_page(request: Request):
    return request.app.state.templates.TemplateResponse(
        "pages/forgot_password.html",
        {"request": request},
    )


@router.post("/forgot-password")
def forgot_submit(request: Request, username: str = Form(...)):
    token = service(request).request_reset(username)

    # DEV ONLY: show link
    if token:
        print(f"RESET LINK: http://localhost:8001/reset-password?token={token}")

    return RedirectResponse("/login?success=reset-sent", status_code=303)


@router.get("/reset-password")
def reset_page(request: Request, token: str):
    return request.app.state.templates.TemplateResponse(
        "pages/reset_password.html",
        {"request": request, "token": token},
    )


@router.post("/reset-password")
def reset_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    if password != password_confirm:
        return RedirectResponse(f"/reset-password?token={token}&error=match", status_code=303)

    ok = service(request).reset_password(token, password)

    if not ok:
        return RedirectResponse("/forgot-password?error=invalid", status_code=303)

    return RedirectResponse("/login?success=reset", status_code=303)