# novelcast/api/router/pages/chapter.py

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.requests import ClientDisconnect

from novelcast.api.deps import (
    get_chapters,
    get_current_user,
    get_progress,
    get_settings,
    get_stories,
    get_templates,
)
from novelcast.services import ChaptersService, ProgressService, SettingsService, StoryService

router = APIRouter()

logger = logging.getLogger(__name__)

# How many chapters beyond the immediate next one to expose to the client
# for background precaching (service worker). This only sends a few
# extra integers in the page — no extra file reads happen here.
PRECACHE_LOOKAHEAD = 3


@router.get("/chapter")
def chapter(
    request: Request,
    story_id: int | None = None,
    chapter_id: int | None = None,
    stories: StoryService = Depends(get_stories),
    chapters: ChaptersService = Depends(get_chapters),
    progress: ProgressService = Depends(get_progress),
    settings_service: SettingsService = Depends(get_settings),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not story_id or not chapter_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = chapters.get_chapter(chapter_id)
    if not chapter or chapter.get("story_id") != story_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = chapters.read_chapter(chapter_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Chapter file missing")

    # Lightweight — IDs only, no N+1 (see ChaptersService.get_downloaded_ids).
    ids = chapters.get_downloaded_ids(story_id)
    idx = next((i for i, cid in enumerate(ids) if cid == chapter_id), None)

    prev_id = ids[idx - 1] if idx is not None and idx > 0 else None
    next_id = ids[idx + 1] if idx is not None and idx < len(ids) - 1 else None

    # A short window of chapter IDs beyond the immediate next one, so the
    # client can hand the service worker several chapters to precache in
    # the background instead of only ever knowing about a single "next".
    upcoming_chapter_ids = ids[idx + 1 : idx + 1 + PRECACHE_LOOKAHEAD] if idx is not None else []

    read_chapters: set[int] = set()
    if current_user and current_user.get("id"):
        prog = progress.get_progress(current_user["id"], story_id)
        if prog and prog.get("last_chapter_id"):
            last = prog["last_chapter_id"]
            read_chapters = {cid for cid in ids if cid <= last}

    first_unread = next((cid for cid in ids if cid not in read_chapters), None)
    hide_author_notes = story.get("hide_author_notes", True)

    reading_settings_schema = settings_service.get_reading_settings_schema()

    return templates.TemplateResponse(
        "pages/chapter.html",
        {
            "request": request,
            "title": story.get("title"),
            "story_link": story.get("source_url"),
            "author": story.get("author"),
            "chapter": chapter.get("title") or f"Chapter {chapter.get('chapter_number')}",
            "content": content,
            "story_id": story_id,
            "chapter_id": chapter_id,
            "prev_chapter_id": prev_id,
            "next_chapter_id": next_id,
            "upcoming_chapter_ids": upcoming_chapter_ids,
            "first_unread_chapter_id": first_unread,
            "hide_author_notes": hide_author_notes,
            "reading_settings_schema": reading_settings_schema,
        },
    )


@router.get("/api/chapter-settings")
async def get_chapter_settings(
    current_user: dict | None = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        chapter_settings = settings_service.get_chapter_reading_settings(current_user["id"], device_id=x_device_id)
        return {"settings": chapter_settings}
    except Exception as e:
        logger.error(f"Error fetching chapter settings for user {current_user['id']}: {e}")
        return {
            "settings": {
                "theme": "light",
                "fontFamily": "serif",
                "fontSize": 100,
                "lineSpacing": 100,
                "fontWeight": 1,
                "paragraphSpacing": 100,
                "contentPadding": 3,
            }
        }


@router.post("/api/chapter-settings")
async def update_chapter_settings(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        body = await request.json()
        data = body.get("settings", {})

        settings_service.save_user_settings(
            user_id=current_user["id"],
            device_id=x_device_id,
            chapter_theme=data.get("theme"),
            chapter_font_family=data.get("fontFamily"),
            chapter_font_size=data.get("fontSize"),
            chapter_line_spacing=data.get("lineSpacing"),
            chapter_font_weight=data.get("fontWeight"),
            chapter_paragraph_spacing=data.get("paragraphSpacing"),
            chapter_content_padding=data.get("contentPadding"),
        )

        return {
            "settings": data,
            "message": "Chapter settings saved successfully",
        }

    except ValueError as e:
        logger.warning(f"Validation error for user {current_user['id']}: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error saving chapter settings for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings") from e


@router.post("/api/chapter-progress")
async def save_chapter_progress(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    progress: ProgressService = Depends(get_progress),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        body = await request.json()
    except ClientDisconnect:
        return {"ok": True}

    chapter_id = body.get("chapter_id")
    story_id = body.get("story_id")
    page = body.get("page", 0)
    total_pages = body.get("total_pages", 1)
    anchor = body.get("anchor", 0)

    if not chapter_id or not story_id:
        raise HTTPException(status_code=400, detail="chapter_id and story_id required")

    progress.set_chapter_page(current_user["id"], chapter_id, page, anchor)

    # "Continue reading" pointer — always follows wherever the person
    # most recently read, even if that's an earlier chapter than one
    # they've read before. No forward-only guard here on purpose.
    progress.set_progress(current_user["id"], story_id, chapter_id, page)

    if page >= total_pages - 1:
        # Furthest-chapter tracking for read/unread marking — this one
        # stays forward-only (enforced inside the repository's upsert),
        # so re-reading an earlier chapter never regresses it.
        progress.advance_furthest_chapter(current_user["id"], story_id, chapter_id, page)

    return {"ok": True}


@router.get("/api/chapter-progress")
async def get_chapter_progress(
    chapter_id: int,
    current_user: dict | None = Depends(get_current_user),
    progress: ProgressService = Depends(get_progress),
):
    if not current_user:
        return {"page": 0, "anchor": None}

    result = progress.get_chapter_page(current_user["id"], chapter_id)
    if isinstance(result, dict):
        return {"page": result.get("page", 0), "anchor": result.get("anchor")}
    return {"page": result or 0, "anchor": None}
