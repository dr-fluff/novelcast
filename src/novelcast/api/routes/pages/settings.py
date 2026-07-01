from urllib.parse import quote

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_settings, get_templates, get_users
from novelcast.services import SettingsService, UserService
from .helpers import parse_settings_form

from fastapi import APIRouter

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

    return templates.TemplateResponse("pages/settings.html", {
        "request":         request,
        "user":            current_user,
        "schema":          settings.schema,
        "user_settings":   user_settings,
        "server_settings": server_settings,
        "users":           all_users,
    })


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

    settings.save_user_settings(
        current_user["id"],
        user_updates.get("theme", "light"),
        user_updates.get("font_size", 14),
        user_updates.get("line_height", 1.5),
        user_updates.get("auto_update", 0),
    )

    if current_user.get("is_root"):
        # Validate Patreon settings before saving if they're being updated
        patreon_updated = False
        for section, fields in server_updates.items():
            if section == "patreon":
                patreon_updated = True
                # Temporarily apply updates for validation
                for key, value in fields.items():
                    settings.set_server_setting(f"{section}.{key}", value)
        
        if patreon_updated:
            # Validate Patreon settings
            ctx = request.app.state.ctx
            patreon_config_service = ctx.engines_config.get("patreon", {}).get("writer")
            if patreon_config_service and hasattr(patreon_config_service, 'validate_settings'):
                is_valid, error_msg = patreon_config_service.validate_settings()
                if not is_valid:
                    active_tab = form.get("_active_tab", "")
                    redirect_url = f"/settings?error={quote(error_msg, safe='')}"
                    if active_tab:
                        redirect_url = f"{redirect_url}#{quote(active_tab, safe='')}"
                    return RedirectResponse(redirect_url, status_code=303)
        
        # Save all settings
        for section, fields in server_updates.items():
            for key, value in fields.items():
                settings.set_server_setting(f"{section}.{key}", value)

    active_tab = form.get("_active_tab", "")
    redirect_url = "/settings?success=1"
    if active_tab:
        redirect_url = f"{redirect_url}#{quote(active_tab, safe='')}"

    return RedirectResponse(redirect_url, status_code=303)
