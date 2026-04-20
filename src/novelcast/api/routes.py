# src/novelcast/api/routes.py

from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import logging

from novelcast.engine.updater import UpdateEngine
from novelcast.core.render import render
from novelcast.services.user_service import UserService

router = APIRouter()
service = UserService()
logger = logging.getLogger(__name__)

# ─────────────────────────────
# Helpers / globals
# ─────────────────────────────
status = {
    "downloading": False,
    "message": "",
    "progress": "",
    "cancel": False
}

DASHBOARD_SORT_OPTIONS = [
    {"key": "title", "label": "Title"},
    {"key": "last_chapter", "label": "Downloaded Chapters"},
    {"key": "url", "label": "URL"},
]

CHAPTER_SORT_OPTIONS = [
    {"key": "name", "label": "Name"},
    {"key": "reverse", "label": "Reverse"},
]

DEFAULT_DASHBOARD_SORT = "title"
DEFAULT_CHAPTER_SORT = "name"


# ─────────────────────────────
# Dashboard
# ─────────────────────────────
@router.get("/")
def home(request: Request):
    db = request.app.state.db

    sort_key = request.query_params.get("sort", "title")

    subs_raw = db.get_subscriptions()
    subs = []

    for s in subs_raw:
        title = s.get("title") or s.get("url")
        subs.append({
            **s,
            "display_title": title,
            "thumbnail_letter": title[0].upper() if title else "N",
        })

    if sort_key == "last_chapter":
        subs.sort(key=lambda x: x.get("last_chapter", 0), reverse=True)
    elif sort_key == "url":
        subs.sort(key=lambda x: (x.get("url") or "").lower())
    else:
        subs.sort(key=lambda x: (x.get("display_title") or "").lower())

    return render(request, "pages/index.html", {
        "subs": subs,
        "sort": sort_key,
    })


# ─────────────────────────────
# Subscribe
# ─────────────────────────────
@router.post("/subscribe")
def subscribe(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    chapters: int = Form(1),
):
    db = request.app.state.db

    if not db.get_subscription(url):
        db.add_subscription(url, title=url)

    background_tasks.add_task(download_story_background, request, url, chapters)

    return RedirectResponse("/", status_code=303)


def download_story_background(request: Request, url: str, chapters: int):
    db = request.app.state.db
    engine = UpdateEngine(db)

    status["downloading"] = True
    status["message"] = "Downloading..."
    status["progress"] = "Starting"

    try:
        success, msg = engine.download_story(url, chapters)

        if not success:
            status["message"] = f"Failed: {msg}"
            status["progress"] = "Error"
        else:
            status["message"] = "Download complete"
            status["progress"] = "Done"

    except Exception as e:
        logger.exception("Download error")
        status["message"] = str(e)
        status["progress"] = "Error"

    finally:
        status["downloading"] = False


# ─────────────────────────────
# API
# ─────────────────────────────
@router.get("/api/status")
def get_status():
    return status


@router.get("/subscriptions")
def subscriptions(request: Request):
    return request.app.state.db.get_subscriptions()


# ─────────────────────────────
# Story page
# ─────────────────────────────
@router.get("/story", response_class=HTMLResponse)
def story(request: Request, url: str):
    db = request.app.state.db

    sub = db.get_subscription(url)

    if not sub or not sub.get("story_path"):
        return render(request, "pages/error.html", {
            "error": "Story not found"
        })
        
    story_path = Path(sub["story_path"])
    chapters = sorted(story_path.glob("*.html"))
    chapter_names = [c.name for c in chapters]

    return render(request, "pages/story.html", {
        "title": sub.get("title"),
        "chapters": chapter_names,
        "url": url,
    })


# ─────────────────────────────
# Chapter page
# ─────────────────────────────
@router.get("/chapter", response_class=HTMLResponse)
def chapter(request: Request, url: str, chapter: str):
    db = request.app.state.db

    sub = db.get_subscription(url)

    if not sub or not sub.get("story_path"):
        return render(request, "pages/error.html", {
            "error": "Story not found"
        })

    file_path = Path(sub["story_path"]) / chapter

    if not file_path.exists():
        return render(request, "pages/error.html", {
            "error": "Chapter not found"
        })

    html = file_path.read_text(encoding="utf-8", errors="ignore")

    return render(request, "pages/chapter.html", {
        "title": sub.get("title"),
        "content": html,
        "chapter": chapter,
    })

@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    templates = request.app.state.templates

    return templates.TemplateResponse(
        "pages/settings.html",
        {"request": request}
    )
    

