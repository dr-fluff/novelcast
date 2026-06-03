# novelcast/api/routes/pages/story.py

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from . import router
from novelcast.api.deps import (
    get_chapter_filter,
    get_chapters,
    get_current_user,
    get_progress,
    get_stories,
    get_templates,
)
from novelcast.services import ChaptersService, ProgressService, StoryService
from novelcast.services.chapter_filter_service import ChapterFilterService
from .helpers import resolve_progress


@router.get("/story")
def story(
    request: Request,
    story_id: int | None = None,
    stories: StoryService = Depends(get_stories),
    chapters: ChaptersService = Depends(get_chapters),
    progress: ProgressService = Depends(get_progress),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not story_id:
        raise HTTPException(status_code=404, detail="Story not found")

    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story_authors = stories.get_story_authors(story_id)
    extra_patterns = get_chapter_filter(request).get_enabled_regexes()
    chapter_list = chapters.list_by_story_filtered(story_id, extra_patterns)
    story_files = stories.get_story_files(story_id)
    read_chapters, last_chapter_id, last_read_title = resolve_progress(
        current_user, story_id, chapter_list, progress, chapters
    )

    first_unread = next(
        (c["id"] for c in chapter_list if c["id"] not in read_chapters), None
    )

    return templates.TemplateResponse("pages/story.html", {
        "request": request,
        "story": story,
        "story_authors": story_authors,
        "chapters": chapter_list,
        "story_files": story_files,
        "read_chapters": read_chapters,
        "last_chapter_id": last_chapter_id,
        "last_read_title": last_read_title,
        "first_unread_chapter_id": first_unread,
    })
