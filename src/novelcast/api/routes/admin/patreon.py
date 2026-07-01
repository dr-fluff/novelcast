# novelcast/api/routes/admin/patreon.py

from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/test")
async def test_patreon(request: Request):
    """Test Patreon OAuth credentials"""
    ctx = request.app.state.ctx
    patreon_config = ctx.engines_config.get("patreon", {})
    patreon_service = patreon_config.get("writer")
    
    if not patreon_service:
        icon = "fa-circle-xmark"
        color = "text-red-500"
        msg = "Patreon service not configured"
        return (
            f"<div class='{color} flex items-center gap-2'>"
            f"<i class='fa-solid {icon}'></i>"
            f"<span>{msg}</span>"
            f"</div>"
        )
    
    # Test with OAuth endpoint check
    is_valid, error_msg = patreon_service.validate_settings(test_oauth=True)
    
    if is_valid:
        icon = "fa-circle-check"
        color = "text-green-500"
        msg = "Patreon credentials are valid!"
    else:
        icon = "fa-circle-xmark"
        color = "text-red-500"
        msg = error_msg or "Unknown error"
    
    return (
        f"<div class='{color} flex items-center gap-2'>"
        f"<i class='fa-solid {icon}'></i>"
        f"<span>{msg}</span>"
        f"</div>"
    )
