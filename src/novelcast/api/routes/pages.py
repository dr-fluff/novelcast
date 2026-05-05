# novelcast/api/routes/pages.py

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter()


# ─────────────────────────────
# TEMPLATE RENDER HELPER
# ─────────────────────────────
def render(request: Request, template: str, context: dict):
    return request.app.state.templates.TemplateResponse(
        template,
        {"request": request, **context},
    )


# ─────────────────────────────
# HOME
# ─────────────────────────────
@router.get("/")
def home(request: Request):
    ctx = request.app.state.ctx

    query = request.query_params.get("q", "").strip().lower()
    sort = request.query_params.get("sort", "title")

    stories = ctx.stories.get_all_stories()

    # search filter
    if query:
        stories = [
            s for s in stories
            if query in (s.get("title") or "").lower()
            or query in (s.get("author") or "").lower()
        ]

    # sorting
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
        if cover_path:
            if cover_path.startswith(("http://", "https://", "/static/")):
                cover_url = cover_path
            else:
                cover_url = f"/covers?path={quote(cover_path)}"

        cards.append({
            "id": s.get("id"),
            "display_title": title,
            "author": s.get("author"),
            "thumbnail_letter": title[0].upper() if title else "?",
            "last_chapter": s.get("downloaded_chapters", 0),
            "cover_url": cover_url,
            "url": f"/story?story_id={s.get('id')}",
        })

    return render(request, "pages/index.html", {
        "stories": cards,
        "sort": sort,
        "query": query,
        "sort_options": [
            {"key": "title", "label": "Title"},
            {"key": "author", "label": "Author"},
            {"key": "downloaded", "label": "Downloaded"},
        ],
    })


# ─────────────────────────────
# STORY PAGE
# ─────────────────────────────
@router.get("/story")
def story(request: Request, story_id: int | None = None):
    if not story_id:
        raise HTTPException(status_code=404, detail="Story not found")

    ctx = request.app.state.ctx
    story = ctx.stories.get_story(story_id)

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    chapters = ctx.chapters.list_by_story(story_id)

    user = getattr(request.state, "user", None)
    read_chapters = set()
    last_chapter_id = None
    last_read_title = None

    if user and user.get("id"):
        progress = ctx.progress.get_progress(user["id"], story_id)

        if progress:
            last_chapter_id = progress.get("last_chapter_id")

            if last_chapter_id:
                last_chapter = ctx.chapters.get_chapter(last_chapter_id)
                if last_chapter:
                    last_read_title = (
                        last_chapter.get("title")
                        or f"Chapter {last_chapter.get('chapter_number')}"
                    )

                read_chapters = {
                    c["id"] for c in chapters if c["id"] <= last_chapter_id
                }

    first_unread = next(
        (c["id"] for c in chapters if c["id"] not in read_chapters),
        None,
    )

    return render(request, "pages/story.html", {
        "story": story,
        "chapters": chapters,
        "read_chapters": read_chapters,
        "last_chapter_id": last_chapter_id,
        "last_read_title": last_read_title,
        "first_unread_chapter_id": first_unread,
    })


# ─────────────────────────────
# CHAPTER PAGE
# ─────────────────────────────
@router.get("/chapter")
def chapter(request: Request, story_id: int | None = None, chapter_id: int | None = None):
    if not story_id or not chapter_id:
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
    ids = [c["id"] for c in chapters]

    try:
        idx = ids.index(chapter_id)
    except ValueError:
        idx = None

    prev_id = ids[idx - 1] if idx is not None and idx > 0 else None
    next_id = ids[idx + 1] if idx is not None and idx < len(ids) - 1 else None

    user = getattr(request.state, "user", None)
    read_chapters = set()

    if user and user.get("id"):
        progress = ctx.progress.get_progress(user["id"], story_id)

        if progress and progress.get("last_chapter_id"):
            last = progress["last_chapter_id"]
            read_chapters = {c["id"] for c in chapters if c["id"] <= last}

        ctx.progress.set_progress(user["id"], story_id, chapter_id, 0)

    first_unread = next(
        (c["id"] for c in chapters if c["id"] not in read_chapters),
        None,
    )

    return render(request, "pages/chapter.html", {
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
def settings(request: Request):
    ctx = request.app.state.ctx
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(status_code=403, detail="Authentication required")

    schema = ctx.settings.schema
    user_settings = ctx.settings.get_user_settings(user["id"])

    server_settings = {}
    users = []

    if user.get("is_root"):
        server_settings = ctx.settings.get_resolved_server_settings()
        users = ctx.users.get_all_users()

    return render(request, "pages/settings.html", {
        "user": user,
        "schema": schema,
        "user_settings": user_settings,
        "server_settings": server_settings,
        "users": users,
    })


@router.post("/settings")
async def save_settings(request: Request):
    ctx = request.app.state.ctx
    user = getattr(request.state, "user", None)

    if not user:
        raise HTTPException(status_code=403, detail="Authentication required")

    form = dict(await request.form())

    user_updates = {}
    server_updates = {}

    for key, value in form.items():
        if "." not in key:
            continue

        section, field = key.split(".", 1)

        if section == "app":
            user_updates.setdefault(field, value)
        else:
            server_updates.setdefault(section, {})[field] = value

    # user settings
    ctx.settings.save_user_settings(
        user["id"],
        user_updates.get("theme", "light"),
        int(user_updates.get("font_size", 14)),
        float(user_updates.get("line_height", 1.5)),
        int(user_updates.get("auto_update", 0)),
    )

    # server settings
    if user.get("is_root"):
        for section, fields in server_updates.items():
            for key, value in fields.items():
                ctx.settings.set_server_setting(f"{section}.{key}", value)

    return RedirectResponse("/settings?success=1", status_code=303)


@router.get("/authors")
def authors(request: Request):
    ctx = request.app.state.ctx
    stories = ctx.stories.get_all_stories()

    authors = {}
    for s in stories:
        author = s.get("author") or "Unknown"
        authors.setdefault(author, []).append(s)

    sorted_authors = sorted(authors.items(), key=lambda x: x[0].lower())

    return render(request, "pages/authors.html", {
        "authors": sorted_authors,
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