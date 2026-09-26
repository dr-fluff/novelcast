# novelcast/api/routes/pages/story.py

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import (
    get_chapters,
    get_current_user,
    get_progress,
    get_settings,
    get_stats,
    get_stories,
    get_templates,
)
from novelcast.services import (
    ChaptersService,
    ProgressService,
    SettingsService,
    StatsService,
    StoryService,
)
from novelcast.core.template_names import TemplateNames
from novelcast.core.template_context import TemplateContext as ContextKey

from .helpers import build_reading_progress_card, resolve_progress
from .preferences import device_preference_key

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/story")
def story(
    request: Request,
    story_id: int | None = None,
    stories: StoryService = Depends(get_stories),
    chapters: ChaptersService = Depends(get_chapters),
    progress: ProgressService = Depends(get_progress),
    settings: SettingsService = Depends(get_settings),
    stats: StatsService = Depends(get_stats),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not story_id:
        raise HTTPException(status_code=404, detail="Story not found")

    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        story_authors = stories.get_story_authors(story_id)
        # extra_patterns = get_chapter_filter(request).get_enabled_regexes()
        chapter_list = chapters.list_by_story_filtered(story_id)
        story_files = None
        progress_row = progress.get_progress(current_user["id"], story_id) if current_user else None

        read_chapters, last_chapter_id, last_read_title = resolve_progress(
            current_user, story_id, chapter_list, progress, chapters, progress_row=progress_row
        )

        first_unread = next((c["id"] for c in chapter_list if c["id"] not in read_chapters), None)
        chapter_data = [
            {
                "id": chapter["id"],
                "chapter_number": chapter["chapter_number"],
                "title": chapter.get("title"),
                "created_at": chapter["created_at"].isoformat() if chapter.get("created_at") else None,
            }
            for chapter in chapter_list
        ]

        progress_card = None
        if current_user and current_user.get("id") and progress_row:
            reading_speed_wpm = stats.get_reading_speed_wpm(current_user["id"])
            progress_card = build_reading_progress_card(
                chapter_list,
                read_chapters,
                last_chapter_id,
                last_read_title,
                progress_row,
                reading_speed_wpm,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    story_preferences = {
        "chapter_sort": "asc",
        "file_sort": "asc",
    }
    device_id = request.cookies.get("novelcast_device_id")
    if current_user and device_id:
        chapter_key = device_preference_key(device_id, "story.chapters.sort")
        file_key = device_preference_key(device_id, "story.files.sort")
        chapter_sort = settings.get_user_preference(current_user["id"], chapter_key, "asc") if chapter_key else "asc"
        file_sort = settings.get_user_preference(current_user["id"], file_key, "asc") if file_key else "asc"
        if chapter_sort in ("asc", "desc"):
            story_preferences["chapter_sort"] = chapter_sort
        if file_sort in ("asc", "desc"):
            story_preferences["file_sort"] = file_sort

    return templates.TemplateResponse(
        TemplateNames.STORY,
        {
            ContextKey.REQUEST: request,
            ContextKey.CURRENT_USER: current_user,
            ContextKey.STORY: story,
            ContextKey.STORY_AUTHORS: story_authors,
            ContextKey.CHAPTERS: chapter_list,
            ContextKey.CHAPTER_DATA: chapter_data,
            ContextKey.STORY_FILES: story_files,
            ContextKey.READ_CHAPTERS: read_chapters,
            ContextKey.LAST_CHAPTER_ID: last_chapter_id,
            ContextKey.LAST_READ_TITLE: last_read_title,
            ContextKey.FIRST_UNREAD_CHAPTER_ID: first_unread,
            ContextKey.STORY_PREFERENCES: story_preferences,
            ContextKey.PROGRESS_CARD: progress_card,
        },
    )


@router.get("/api/story-files/{story_id}")
def story_files(
    request: Request,
    story_id: int,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    return templates.TemplateResponse(
        TemplateNames.STORY_FILES,
        {
            ContextKey.REQUEST: request,
            ContextKey.STORY_FILES: stories.get_story_files(story_id),
        },
    )

@router.delete("/api/story-progress/{story_id}")
async def delete_story_progress(
    story_id: int,
    current_user: dict | None = Depends(get_current_user),
    progress: ProgressService = Depends(get_progress),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    progress.delete_progress(current_user["id"], story_id)
    return {"ok": True}