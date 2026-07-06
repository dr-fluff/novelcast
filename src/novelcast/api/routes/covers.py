# novelcast/api/routes/covers.py

import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from novelcast.api.deps import get_stories
from novelcast.services import StoryService

router = APIRouter(prefix="/stories", tags=["covers"])

COVERS_DIR = (Path(__file__).resolve().parent.parent / "data" / "covers").resolve()
COVERS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_COVER_BYTES = 8 * 1024 * 1024  # 8 MB


class CoverFromUrl(BaseModel):
    url: str


def _cover_url(filename: str) -> str:
    return f"/covers?path={filename}"


def _save_cover_bytes(story_id: int, data: bytes, content_type: str | None) -> str:
    ext = ALLOWED_CONTENT_TYPES.get((content_type or "").split(";")[0].strip())
    if not ext:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {content_type}")
    if len(data) > MAX_COVER_BYTES:
        raise HTTPException(status_code=400, detail="Image too large (max 8MB)")

    filename = f"{story_id}-{uuid.uuid4().hex[:8]}{ext}"
    (COVERS_DIR / filename).write_bytes(data)
    return filename


def _delete_existing_cover(cover_path: str | None):
    if not cover_path:
        return
    old = (COVERS_DIR / Path(cover_path).name).resolve()
    if old.is_relative_to(COVERS_DIR) and old.exists():
        old.unlink(missing_ok=True)


@router.post("/{story_id}/cover")
async def upload_cover(
    request: Request,
    story_id: int,
    file: UploadFile = File(...),
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    data = await file.read()
    filename = _save_cover_bytes(story_id, data, file.content_type)

    _delete_existing_cover(story.get("cover_path"))
    stories.update_story_cover(story_id, filename)
    request.app.state.ctx.emit("story_updated", {"story_id": story_id})

    return {"status": "ok", "cover_url": _cover_url(filename)}


@router.post("/{story_id}/cover/from-url")
async def set_cover_from_url(
    request: Request,
    story_id: int,
    body: CoverFromUrl,
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch image: {e}") from e

    filename = _save_cover_bytes(story_id, resp.content, resp.headers.get("content-type"))

    _delete_existing_cover(story.get("cover_path"))
    stories.update_story_cover(story_id, filename)
    request.app.state.ctx.emit("story_updated", {"story_id": story_id})

    return {"status": "ok", "cover_url": _cover_url(filename)}


@router.delete("/{story_id}/cover")
def delete_cover(
    request: Request,
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    _delete_existing_cover(story.get("cover_path"))
    stories.update_story_cover(story_id, None)
    request.app.state.ctx.emit("story_updated", {"story_id": story_id})

    return {"status": "ok"}