# novelcast/api/routes/pages.py

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import (
    get_chapters,
    get_current_user,
    get_progress,
    get_settings,
    get_stories,
    get_templates,
    get_users,
)

from novelcast.services import (
    StoryService,
    ProgressService,
    SettingsService,
    UserService,
    ChaptersService,
)


router = APIRouter(tags=["pages"])


# ─────────────────────────────
# HOME
# ─────────────────────────────
@router.get("/")
def home(
    request: Request,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    query = request.query_params.get("q", "").strip().lower()
    sort = request.query_params.get("sort", "title")

    all_stories = stories.get_all_stories()
    all_stories = _filter_stories(all_stories, query)
    all_stories = _sort_stories(all_stories, sort)

    cards = [_story_card(s) for s in all_stories]

    return templates.TemplateResponse("pages/index.html", {
        "request": request,
        "stories": cards,
        "sort": sort,
        "query": query,
        "sort_options": [
            {"key": "title",      "label": "Title"},
            {"key": "author",     "label": "Author"},
            {"key": "downloaded", "label": "Downloaded"},
        ],
    })


# ─────────────────────────────
# STORY PAGE
# ─────────────────────────────
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

    chapter_list = chapters.list_by_story(story_id)
    read_chapters, last_chapter_id, last_read_title = _resolve_progress(
        current_user, story_id, chapter_list, progress, chapters
    )

    first_unread = next(
        (c["id"] for c in chapter_list if c["id"] not in read_chapters), None
    )

    return templates.TemplateResponse("pages/story.html", {
        "request": request,
        "story": story,
        "chapters": chapter_list,
        "read_chapters": read_chapters,
        "last_chapter_id": last_chapter_id,
        "last_read_title": last_read_title,
        "first_unread_chapter_id": first_unread,
    })


# ─────────────────────────────
# CHAPTER PAGE
# ─────────────────────────────
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


# ─────────────────────────────
# SETTINGS
# ─────────────────────────────
@router.get("/settings")
def settings(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")

    user_settings = settings.get_user_settings(current_user["id"])
    server_settings = {}
    all_users = []

    if current_user.get("is_root"):
        server_settings = settings.get_display_server_settings()
        all_users = users.get_all_users()

    return templates.TemplateResponse("pages/settings.html", {
        "request": request,
        "user": current_user,
        "schema": settings.schema,
        "user_settings": user_settings,
        "server_settings": server_settings,
        "users": all_users,
    })


@router.post("/settings")
async def save_settings(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")

    form = dict(await request.form())
    user_updates, server_updates = _parse_settings_form(form)

    settings.save_user_settings(
        current_user["id"],
        user_updates.get("theme", "light"),
        int(user_updates.get("font_size", 14)),
        float(user_updates.get("line_height", 1.5)),
        int(user_updates.get("auto_update", 0)),
    )

    if current_user.get("is_root"):
        for section, fields in server_updates.items():
            for key, value in fields.items():
                settings.set_server_setting(f"{section}.{key}", value)

    return RedirectResponse("/settings?success=1", status_code=303)


# ─────────────────────────────
# AUTHORS
# ─────────────────────────────
@router.get("/authors")
def authors(
    request: Request,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    query = request.query_params.get("q", "").strip().lower()
    sort  = request.query_params.get("sort", "name")

    all_authors = stories.get_all_authors(query=query, sort=sort)

    return templates.TemplateResponse("pages/authors.html", {
        "request":      request,
        "authors":      all_authors,
        "query":        query,
        "sort":         sort,
        "sort_options": [
            {"key": "name",    "label": "Name (A–Z)"},
            {"key": "stories", "label": "Most stories"},
            {"key": "updated", "label": "Last updated"},
            {"key": "added",   "label": "Date added"},
        ],
    })


@router.get("/authors/{author_id}")
def author_detail(
    request: Request,
    author_id: int,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    author = stories.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    return templates.TemplateResponse("pages/author.html", {
        "request": request,
        "author":  author,
    })

# ─────────────────────────────
# COVERS (SAFE FILE ACCESS)
# ─────────────────────────────
@router.get("/covers")
def get_cover(path: str):
    file_path = Path(path).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(file_path)


# ─────────────────────────────
# FAVICON
# ─────────────────────────────
@router.get("/favicon.svg")
def favicon():
    path = Path(__file__).resolve().parent.parent / "static/images/favicon.svg"
    return FileResponse(path, media_type="image/svg+xml")


# ─────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────
def _filter_stories(stories: list[dict], query: str) -> list[dict]:
    if not query:
        return stories
    return [
        s for s in stories
        if query in (s.get("title") or "").lower()
        or query in (s.get("author") or "").lower()
    ]


def _sort_stories(stories: list[dict], sort: str) -> list[dict]:
    if sort == "author":
        return sorted(stories, key=lambda s: (s.get("author") or "").lower())
    if sort == "downloaded":
        return sorted(stories, key=lambda s: s.get("downloaded_chapters", 0), reverse=True)
    return sorted(stories, key=lambda s: (s.get("title") or "").lower())


def _story_card(s: dict) -> dict:
    title = s.get("title") or "Untitled"
    cover_path = s.get("cover_path")

    if cover_path and not cover_path.startswith(("http://", "https://", "/static/")):
        cover_url = f"/covers?path={quote(cover_path)}"
    else:
        cover_url = cover_path

    return {
        "id": s.get("id"),
        "display_title": title,
        "author": s.get("author"),
        "thumbnail_letter": title[0].upper() if title else "?",
        "last_chapter": s.get("downloaded_chapters", 0),
        "cover_url": cover_url,
        "url": f"/story?story_id={s.get('id')}",
    }


def _resolve_progress(
    user: dict | None,
    story_id: int,
    chapter_list: list[dict],
    progress: ProgressService,
    chapters: ChaptersService,
) -> tuple[set[int], int | None, str | None]:
    read_chapters: set[int] = set()
    last_chapter_id = None
    last_read_title = None

    if user and user.get("id"):
        prog = progress.get_progress(user["id"], story_id)
        if prog:
            last_chapter_id = prog.get("last_chapter_id")
            if last_chapter_id:
                last_chapter = chapters.get_chapter(last_chapter_id)
                if last_chapter:
                    last_read_title = (
                        last_chapter.get("title")
                        or f"Chapter {last_chapter.get('chapter_number')}"
                    )
                read_chapters = {c["id"] for c in chapter_list if c["id"] <= last_chapter_id}

    return read_chapters, last_chapter_id, last_read_title


def _parse_settings_form(form: dict) -> tuple[dict, dict]:
    user_updates: dict = {}
    server_updates: dict = {}

    for key, value in form.items():
        if "." not in key:
            continue
        section, field = key.split(".", 1)
        if section == "app":
            user_updates.setdefault(field, value)
        else:
            server_updates.setdefault(section, {})[field] = value

    return user_updates, server_updates
