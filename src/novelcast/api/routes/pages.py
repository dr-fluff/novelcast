from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


def render(request: Request, template: str, context: dict):
    return request.app.state.templates.TemplateResponse(
        template,
        {"request": request, **context},
    )


@router.get("/")
def home(request: Request):
    ctx = request.app.state.ctx
    query = request.query_params.get("q", "").strip()
    sort = request.query_params.get("sort", "title")

    sort_options = [
        {"key": "title", "label": "Title"},
        {"key": "author", "label": "Author"},
        {"key": "downloaded", "label": "Downloaded"},
    ]

    stories = ctx.stories.get_all_stories()

    if query:
        query_lower = query.lower()
        stories = [
            s for s in stories
            if query_lower in (s.get("title") or "").lower()
            or query_lower in (s.get("author") or "").lower()
        ]

    if sort == "author":
        stories.sort(key=lambda s: (s.get("author") or "").lower())
    elif sort == "downloaded":
        stories.sort(key=lambda s: s.get("downloaded_chapters", 0), reverse=True)
    else:
        stories.sort(key=lambda s: (s.get("title") or "").lower())

    cards = []
    for s in stories:
        title = s.get("title") or "Untitled"
        cover_path = s.get("cover_path")
        cover_url = None
        if cover_path and (cover_path.startswith("http://") or cover_path.startswith("https://") or cover_path.startswith("/static/")):
            cover_url = cover_path

        cards.append({
            "id": s.get("id"),
            "display_title": title,
            "author": s.get("author"),
            "thumbnail_letter": title[0].upper() if title else "?",
            "last_chapter": s.get("downloaded_chapters", 0),
            "cover_url": cover_url,
            "url": f"/story?story_id={s.get('id')}",
        })

    return render(
        request,
        "pages/index.html",
        {
            "stories": cards,
            "sort_options": sort_options,
            "sort": sort,
            "query": query,
        },
    )


@router.get("/story")
def story(request: Request, story_id: int | None = None):
    if story_id is None:
        raise HTTPException(status_code=404, detail="Story not found")

    ctx = request.app.state.ctx
    story = ctx.stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapters = ctx.chapters.list_by_story(story_id)

    last_chapter_id = None
    last_read_title = None
    read_chapters = set()
    user = getattr(request.state, "user", None)
    if user and user.get("id"):
        progress = ctx.progress.get_progress(user["id"], story_id)
        if progress:
            last_chapter_id = progress.get("last_chapter_id")
            if last_chapter_id:
                last_chapter = ctx.chapters.get_chapter(last_chapter_id)
                if last_chapter:
                    last_read_title = last_chapter.get("title") or f"Chapter {last_chapter.get('chapter_number')}"
                read_chapters = {
                    chapter["id"]
                    for chapter in chapters
                    if chapter["id"] <= last_chapter_id
                }

    return render(
        request,
        "pages/story.html",
        {
            "story": story,
            "chapters": chapters,
            "read_chapters": read_chapters,
            "last_chapter_id": last_chapter_id,
            "last_read_title": last_read_title,
        },
    )


@router.get("/chapter")
def chapter(request: Request, story_id: int | None = None, chapter_id: int | None = None):
    if story_id is None or chapter_id is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    ctx = request.app.state.ctx
    story = ctx.stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapter = ctx.chapters.get_chapter(chapter_id)
    if not chapter or chapter.get("story_id") != story_id:
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = ctx.chapters.read_chapter(chapter_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Chapter file missing")

    chapters = ctx.chapters.list_by_story(story_id)
    chapter_ids = [c["id"] for c in chapters]
    current_index = chapter_ids.index(chapter_id) if chapter_id in chapter_ids else None
    prev_chapter_id = chapter_ids[current_index - 1] if current_index is not None and current_index > 0 else None
    next_chapter_id = chapter_ids[current_index + 1] if current_index is not None and current_index < len(chapter_ids) - 1 else None

    user = getattr(request.state, "user", None)
    if user and user.get("id"):
        ctx.progress.set_progress(user["id"], story_id, chapter_id, 0)

    return render(
        request,
        "pages/chapter.html",
        {
            "title": story.get("title"),
            "author": story.get("author"),
            "chapter": chapter.get("title") or f"Chapter {chapter.get('chapter_number')}",
            "content": content,
            "story_id": story_id,
            "chapter_id": chapter_id,
            "prev_chapter_id": prev_chapter_id,
            "next_chapter_id": next_chapter_id,
        },
    )

@router.get("/settings")
def settings(request: Request):
    return render(
        request,
        "pages/settings.html",
        {}
    )