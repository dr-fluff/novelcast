# novelcast/api/routes/pages/story.py

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import (
    get_chapters,
    get_current_user,
    get_progress,
    get_settings,
    get_stories,
    get_templates,
)
from novelcast.services import (
    ChaptersService,
    ProgressService,
    SettingsService,
    StoryService,
)

from .helpers import resolve_progress
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
        story_files = stories.get_story_files(story_id)

        read_chapters, last_chapter_id, last_read_title = resolve_progress(
            current_user, story_id, chapter_list, progress, chapters
        )

        first_unread = next((c["id"] for c in chapter_list if c["id"] not in read_chapters), None)
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
        "pages/story.html",
        {
            "request": request,
            "current_user": current_user,
            "story": story,
            "story_authors": story_authors,
            "chapters": chapter_list,
            "story_files": story_files,
            "read_chapters": read_chapters,
            "last_chapter_id": last_chapter_id,
            "last_read_title": last_read_title,
            "first_unread_chapter_id": first_unread,
            "story_preferences": story_preferences,
        },
    )
