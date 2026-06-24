import re

from fastapi import Depends, HTTPException, Request, APIRouter

from novelcast.api.deps import get_current_user, get_settings
from novelcast.services import SettingsService

router = APIRouter()

_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
_ALLOWED_NAMES = {
    "library.index",
    "story.chapters.sort",
    "story.files.sort",
}


def device_preference_key(device_id: str | None, name: str) -> str | None:
    if not device_id or name not in _ALLOWED_NAMES or not _DEVICE_RE.match(device_id):
        return None
    return f"device.{device_id}.{name}"


@router.post("/api/user-preferences")
async def save_user_preference(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    settings: SettingsService = Depends(get_settings),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    body = await request.json()
    name = str(body.get("name") or "")
    device_id = str(body.get("deviceId") or request.cookies.get("novelcast_device_id") or "")
    key = device_preference_key(device_id, name)
    if not key:
        raise HTTPException(status_code=400, detail="Invalid preference")

    value = body.get("value")
    settings.set_user_preference(current_user["id"], key, value)
    return {"ok": True}


@router.delete("/api/user-preferences")
async def delete_user_preference(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    settings: SettingsService = Depends(get_settings),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    body = await request.json()
    name = str(body.get("name") or "")
    device_id = str(body.get("deviceId") or request.cookies.get("novelcast_device_id") or "")
    key = device_preference_key(device_id, name)
    if not key:
        raise HTTPException(status_code=400, detail="Invalid preference")

    settings.delete_user_preference(current_user["id"], key)
    return {"ok": True}
