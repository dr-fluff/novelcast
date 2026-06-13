from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

import logging

from . import router
from novelcast.api.deps import get_chapters, get_current_user, get_progress, get_stories, get_templates, get_settings
from novelcast.services import ChaptersService, ProgressService, StoryService
from novelcast.services import SettingsService


logger = logging.getLogger(__name__)

@router.get("/chapter")
def chapter(
    request: Request,
    story_id: int | None = None,
    chapter_id: int | None = None,
    stories: StoryService = Depends(get_stories),
    chapters: ChaptersService = Depends(get_chapters),
    progress: ProgressService = Depends(get_progress),
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

    chapter_list = chapters.list_by_story(story_id)
    ids = [c["id"] for c in chapter_list]
    idx = next((i for i, cid in enumerate(ids) if cid == chapter_id), None)

    prev_id = ids[idx - 1] if idx is not None and idx > 0 else None
    next_id = ids[idx + 1] if idx is not None and idx < len(ids) - 1 else None

    logger.info("prev_id: %s, next_id: %s", prev_id, next_id)
    read_chapters: set[int] = set()
    if current_user and current_user.get("id"):
        prog = progress.get_progress(current_user["id"], story_id)
        if prog and prog.get("last_chapter_id"):
            last = prog["last_chapter_id"]
            read_chapters = {c["id"] for c in chapter_list if c["id"] <= last}

    first_unread = next(
        (c["id"] for c in chapter_list if c["id"] not in read_chapters), None
    )
    hide_author_notes = story.get("hide_author_notes", True)

    return templates.TemplateResponse("pages/chapter.html", {
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
    })


@router.get("/api/chapter-settings")
async def get_chapter_settings(
    current_user: dict | None = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings),
):

    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        chapter_settings = settings_service.get_chapter_reading_settings(
            current_user["id"]
        )
        return {"settings": chapter_settings}
    except Exception as e:
        logger.error(f"Error fetching chapter settings for user {current_user['id']}: {e}")
        # Return defaults on error
        return {
            "settings": {
                "theme": "light",
                "fontFamily": "serif",
                "fontSize": 100,
                "lineSpacing": 100,
                "fontWeight": 0,
                "paragraphSpacing": 100,
            }
        }


@router.post("/api/chapter-settings")
async def update_chapter_settings(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        body = await request.json()
        data = body.get("settings", {})

        # Validate ranges to prevent invalid data
        if "fontSize" in data:
            fs = data["fontSize"]
            if not (80 <= fs <= 170):
                raise ValueError("fontSize must be between 80 and 170")
        
        if "lineSpacing" in data:
            ls = data["lineSpacing"]
            if not (80 <= ls <= 150):
                raise ValueError("lineSpacing must be between 80 and 150")
        
        if "paragraphSpacing" in data:
            ps = data["paragraphSpacing"]
            if not (50 <= ps <= 200):
                raise ValueError("paragraphSpacing must be between 50 and 200")

        # Save via SettingsService
        # Pass None for display settings so we only update chapter settings
        settings_service.save_user_settings(
            user_id=current_user["id"],
            theme=None,           # Don't update UI theme from chapter API
            font_size=None,       # Don't update UI font size from chapter API
            line_height=None,     # Don't update UI line height from chapter API
            auto_update=None,     # Don't update auto_update from chapter API
            # Only update chapter reading settings
            chapter_theme=data.get("theme"),
            chapter_font_family=data.get("fontFamily"),
            chapter_font_size=data.get("fontSize"),
            chapter_line_spacing=data.get("lineSpacing"),
            chapter_font_weight=data.get("fontWeight"),
            chapter_paragraph_spacing=data.get("paragraphSpacing"),
        )

        # Return the settings that were saved
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
    

from starlette.requests import ClientDisconnect

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

    chapter_id  = body.get("chapter_id")
    story_id    = body.get("story_id")
    page        = body.get("page", 0)
    total_pages = body.get("total_pages", 1)
    anchor      = body.get("anchor", 0)

    if not chapter_id or not story_id:
        raise HTTPException(status_code=400, detail="chapter_id and story_id required")

    progress.set_chapter_page(current_user["id"], chapter_id, page, anchor)

    if page >= total_pages - 1:
        progress.set_progress(current_user["id"], story_id, chapter_id, page)

    return {"ok": True}


@router.get("/api/chapter-progress")
async def get_chapter_progress(
    chapter_id: int,
    current_user: dict | None = Depends(get_current_user),
    progress: ProgressService = Depends(get_progress),
):
    if not current_user:
        return {"page": 0}

    page = progress.get_chapter_page(current_user["id"], chapter_id)
    return {"page": page or 0}