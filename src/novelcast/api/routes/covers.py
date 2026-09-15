# novelcast/api/routes/covers.py

import uuid
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, HttpUrl

from novelcast.api.deps import get_stories
from novelcast.services import StoryService

router = APIRouter(prefix="/stories", tags=["covers"])
logger = logging.getLogger(__name__)

COVERS_DIR = (Path.cwd().resolve() / "data" / "covers").resolve()
COVERS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_COVER_BYTES = 8 * 1024 * 1024  # 8 MB

JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WEBP_RIFF_SIGNATURE = b"RIFF"
WEBP_FORMAT_SIGNATURE = b"WEBP"


class CoverFromUrl(BaseModel):
    url: HttpUrl


def _cover_url(filename: str) -> str:
    return f"/covers?path={filename}"


def _image_extension(data: bytes, content_type: str | None) -> str | None:
    """Determine the image type from bytes before trusting a remote header."""
    if data.startswith(JPEG_SIGNATURE):
        return ".jpg"
    if data.startswith(PNG_SIGNATURE):
        return ".png"
    if len(data) >= 12 and data.startswith(WEBP_RIFF_SIGNATURE) and data[8:12] == WEBP_FORMAT_SIGNATURE:
        return ".webp"
    return ALLOWED_CONTENT_TYPES.get((content_type or "").split(";")[0].strip())


def _save_cover_bytes(story_id: int, data: bytes, content_type: str | None) -> str:
    ext = _image_extension(data, content_type)
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
            resp = await client.get(str(body.url))
            resp.raise_for_status()
    except httpx.HTTPError as e:
        # A remote image URL is a supported cover path.  Keep it as a link
        # when the server cannot fetch it (for example, due to DNS or CDN
        # restrictions) so the user's browser can still load the cover.
        logger.warning("Could not download remote cover for story %s: %s", story_id, e)
        _delete_existing_cover(story.get("cover_path"))
        cover_url = str(body.url)
        stories.update_story_cover(story_id, cover_url)
        request.app.state.ctx.emit("story_updated", {"story_id": story_id})
        return {"status": "linked", "cover_url": cover_url}

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
