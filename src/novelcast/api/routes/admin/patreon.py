# novelcast/api/routes/admin/patreon.py

from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/test")
async def test_patreon(request: Request):
    """Test the configured Patreon session cookie"""
    ctx = request.app.state.ctx

    is_valid, error_msg = ctx.patreon_engine.validate_settings(test_oauth=True)

    if is_valid:
        icon, color, msg = (
            "fa-circle-check",
            "text-green-500",
            "Patreon session cookie is valid!",
        )
    else:
        icon, color = "fa-circle-xmark", "text-red-500"
        msg = error_msg or "Unknown error"
        ctx.settings.set_server_setting("patreon.enabled", False)

    return f"<div class='{color} flex items-center gap-2'><i class='fa-solid {icon}'></i><span>{msg}</span></div>"
