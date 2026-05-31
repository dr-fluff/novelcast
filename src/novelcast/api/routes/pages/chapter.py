from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from . import router
from novelcast.api.deps import get_chapters, get_current_user, get_progress, get_stories, get_templates
from novelcast.services import ChaptersService, ProgressService, StoryService


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

    read_chapters: set[int] = set()
    if current_user and current_user.get("id"):
        prog = progress.get_progress(current_user["id"], story_id)
        if prog and prog.get("last_chapter_id"):
            last = prog["last_chapter_id"]
            read_chapters = {c["id"] for c in chapter_list if c["id"] <= last}
        progress.set_progress(current_user["id"], story_id, chapter_id, 0)

    first_unread = next(
        (c["id"] for c in chapter_list if c["id"] not in read_chapters), None
    )

    return templates.TemplateResponse("pages/chapter.html", {
        "request": request,
        "title": story.get("title"),
        "author": story.get("author"),
        "chapter": chapter.get("title") or f"Chapter {chapter.get('chapter_number')}",
        "content": content,
        "story_id": story_id,
        "chapter_id": chapter_id,
        "prev_chapter_id": prev_id,
        "next_chapter_id": next_id,
        "first_unread_chapter_id": first_unread,
    })
