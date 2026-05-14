# novelcast/api/routes/password_reset.py

import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_password_reset, get_templates
from novelcast.services import PasswordResetService

log = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/forgot-password")
def forgot_page(templates: Jinja2Templates = Depends(get_templates)):
    # templates.TemplateResponse requires a Request; handled via middleware/dependency upstream
    return templates.TemplateResponse("pages/forgot_password.html", {})


@router.post("/forgot-password")
def forgot_submit(
    username: str = Form(...),
    service: PasswordResetService = Depends(get_password_reset),
):
    token = service.request_reset(username)

    if token:
        # DEV ONLY: replace with email delivery in production
        log.debug("RESET LINK: http://localhost:8001/reset-password?token=%s", token)

    return RedirectResponse("/login?success=reset-sent", status_code=303)


@router.get("/reset-password")
def reset_page(
    token: str,
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse("pages/reset_password.html", {"token": token})


@router.post("/reset-password")
def reset_submit(
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    service: PasswordResetService = Depends(get_password_reset),
):
    if password != password_confirm:
        return RedirectResponse(f"/reset-password?token={token}&error=match", status_code=303)

    if not service.reset_password(token, password):
        return RedirectResponse("/forgot-password?error=invalid", status_code=303)

    return RedirectResponse("/login?success=reset", status_code=303)