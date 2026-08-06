from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_settings, get_templates, get_users
from novelcast.services import SettingsService, UserService

from .helpers import parse_settings_form

router = APIRouter()


@router.get("/settings")
def settings(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")

    user_settings = settings.get_user_settings(current_user["id"])
    server_settings = {}
    all_users = []

    if current_user.get("is_root"):
        server_settings = settings.get_scoped_server_settings()
        all_users = users.get_all_users()

    return templates.TemplateResponse(
        "pages/settings.html",
        {
            "request": request,
            "user": current_user,
            "schema": settings.schema,
            "user_settings": user_settings,
            "server_settings": server_settings,
            "users": all_users,
        },
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")

    form = dict(await request.form())
    user_updates, server_updates = parse_settings_form(form)

    settings.save_user_settings(current_user["id"], **user_updates)

    if current_user.get("is_root"):
        # Save site overrides via the dedicated method
        fanficfare_updates = server_updates.get("fanficfare", {})
        site_overrides = fanficfare_updates.pop("site_overrides", {})
        for domain, domain_fields in site_overrides.items():
            for field, value in domain_fields.items():
                settings.set_site_override(domain, field, value)

        # Validate Patreon settings before saving if they're being updated
        patreon_updated = False
        for section, fields in server_updates.items():
            if section == "patreon":
                patreon_updated = True
                for key, value in fields.items():
                    settings.set_server_setting(f"{section}.{key}", value)

        if patreon_updated:
            ctx = request.app.state.ctx
            patreon_config_service = ctx.engines_config.get("patreon", {}).get("writer")
            if patreon_config_service and hasattr(patreon_config_service, "validate_settings"):
                is_valid, error_msg = patreon_config_service.validate_settings()
                if not is_valid:
                    active_tab = form.get("_active_tab", "")
                    redirect_url = f"/settings?error={quote(error_msg, safe='')}"
                    if active_tab:
                        redirect_url = f"{redirect_url}#{quote(active_tab, safe='')}"
                    return RedirectResponse(redirect_url, status_code=303)

        # Save remaining flat settings (skip patreon, already saved above)
        for section, fields in server_updates.items():
            if section == "patreon":
                continue
            for key, value in fields.items():
                settings.set_server_setting(f"{section}.{key}", value)

    active_tab = form.get("_active_tab", "")
    redirect_url = "/settings?success=1"
    if active_tab:
        redirect_url = f"{redirect_url}#{quote(active_tab, safe='')}"

    return RedirectResponse(redirect_url, status_code=303)
