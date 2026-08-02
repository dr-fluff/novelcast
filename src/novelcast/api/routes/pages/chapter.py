# novelcast/api/router/pages/chapter.py
# novelcast/api/router/chapter.py
#
# TEMP DIAGNOSTIC VERSION — adds timing logs around each step of the
# /chapter route so we can see where the actual latency is coming from
# (DB queries, file I/O, template render, etc.) before deciding on a fix.
# Remove the `t0 = ...` / `logger.info("TIMING: ...")` lines once done.

import logging
import time

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
    t_start = time.perf_counter()

    if not story_id or not chapter_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    t0 = time.perf_counter()
    story = stories.get_story(story_id)
    logger.info("TIMING get_story: %.1fms", (time.perf_counter() - t0) * 1000)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    t0 = time.perf_counter()
    chapter = chapters.get_chapter(chapter_id)
    logger.info("TIMING get_chapter: %.1fms", (time.perf_counter() - t0) * 1000)
    if not chapter or chapter.get("story_id") != story_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    t0 = time.perf_counter()
    content = chapters.read_chapter(chapter_id)
    logger.info("TIMING read_chapter (file I/O): %.1fms", (time.perf_counter() - t0) * 1000)
    if content is None:
        raise HTTPException(status_code=404, detail="Chapter file missing")

    t0 = time.perf_counter()
    chapter_list = chapters.list_by_story(story_id)
    logger.info(
        "TIMING list_by_story (%d chapters): %.1fms",
        len(chapter_list),
        (time.perf_counter() - t0) * 1000,
    )

    ids = [c["id"] for c in chapter_list]
    idx = next((i for i, cid in enumerate(ids) if cid == chapter_id), None)

    prev_id = ids[idx - 1] if idx is not None and idx > 0 else None
    next_id = ids[idx + 1] if idx is not None and idx < len(ids) - 1 else None

    logger.info("prev_id: %s, next_id: %s", prev_id, next_id)
    read_chapters: set[int] = set()

    t0 = time.perf_counter()
    if current_user and current_user.get("id"):
        prog = progress.get_progress(current_user["id"], story_id)
        if prog and prog.get("last_chapter_id"):
            last = prog["last_chapter_id"]
            read_chapters = {c["id"] for c in chapter_list if c["id"] <= last}
    logger.info("TIMING progress/read_chapters: %.1fms", (time.perf_counter() - t0) * 1000)

    first_unread = next((c["id"] for c in chapter_list if c["id"] not in read_chapters), None)
    hide_author_notes = story.get("hide_author_notes", True)

    t0 = time.perf_counter()
    reading_settings_schema = settings_service.get_reading_settings_schema()
    logger.info("TIMING get_reading_settings_schema: %.1fms", (time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    response = templates.TemplateResponse(
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
            "first_unread_chapter_id": first_unread,
            "hide_author_notes": hide_author_notes,
            "reading_settings_schema": reading_settings_schema,
        },
    )
    logger.info("TIMING template render: %.1fms", (time.perf_counter() - t0) * 1000)

    logger.info("TIMING TOTAL /chapter: %.1fms", (time.perf_counter() - t_start) * 1000)

    return response


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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving chapter settings for user {current_user['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings")


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

    if page >= total_pages - 1:
        # Only advance story progress, never move it backwards
        current = progress.get_progress(current_user["id"], story_id)
        current_last = (current or {}).get("last_chapter_id") or 0
        if chapter_id >= current_last:
            progress.set_progress(current_user["id"], story_id, chapter_id, page)

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