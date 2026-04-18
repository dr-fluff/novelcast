from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.storage.db import Database
from novelcast.engine.updater import UpdateEngine

from pathlib import Path
from urllib.parse import urlparse, quote
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup
import requests
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

LOG_FILE = Path.cwd() / "novelcast.log"

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

# Global status for background tasks
status = {"downloading": False, "message": "", "progress": "", "cancel": False}


def get_log_tail(limit: int = 50) -> list[str]:
    if not LOG_FILE.exists():
        return []

    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-limit:]]
    except Exception as e:
        logger.error("Unable to read log file: %s", e)
        return []


def render_error(request: Request, error_message: str) -> HTMLResponse:
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "error": error_message,
            "log": get_log_tail()
        }
    )

db = Database()
engine = UpdateEngine(db)

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = APP_DIR / "web/templates"
STATIC_DIR = WEB_DIR / "static"

templates = Jinja2Templates(
    directory=str(APP_DIR / "web/templates")
)

# URL filter for Jinja
def safe_urlencode(value):
    return quote(str(value)) if value else ""

templates.env.filters["urlencode"] = safe_urlencode
templates.env.auto_reload = True


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def build_display_title(sub: dict) -> str:
    title = sub.get("title")

    if title and title != "Unknown":
        return title

    parsed = urlparse(sub.get("url", ""))

    fallback = parsed.path.strip("/").split("/")[-1] if parsed.path else sub.get("url", "Unknown")

    return fallback.replace("-", " ").replace("_", " ").title()


def sort_subscriptions(subs: list[dict], sort_key: str) -> list[dict]:
    if sort_key == "last_chapter":
        return sorted(subs, key=lambda s: s.get("last_chapter") or 0, reverse=True)
    if sort_key == "url":
        return sorted(subs, key=lambda s: (s.get("url") or "").lower())
    return sorted(subs, key=lambda s: (s.get("display_title") or "").lower())


def sort_chapters(chapters: list[str], sort_key: str) -> list[str]:
    if sort_key == "reverse":
        return sorted(chapters, reverse=True)
    return sorted(chapters)


def enrich_subscription(sub: dict) -> dict:
    title = build_display_title(sub)

    return {
        **sub,
        "display_title": title,
        "thumbnail_letter": title[:1].upper() if title else "N",
    }


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    sort_key = request.query_params.get("sort", DEFAULT_DASHBOARD_SORT)
    subs_raw = db.get_subscriptions()
    subs = [enrich_subscription(s) for s in subs_raw]
    subs = sort_subscriptions(subs, sort_key)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "subs": subs,
            "sort": sort_key,
            "sort_options": DASHBOARD_SORT_OPTIONS
        }
    )


# ─────────────────────────────────────────────
# Subscribe
# ─────────────────────────────────────────────

@router.post("/subscribe")
def subscribe(request: Request, url: str = Form(...), chapters: int = Form(1), background_tasks: BackgroundTasks = None):
    logger.info("Subscribing to %s (%s chapters)", url, chapters)

    existing = db.get_subscription(url)

    if not existing:
        db.add_subscription(url, title=url)

    # Start download in background
    background_tasks.add_task(download_story_background, url, chapters)

    return RedirectResponse("/", status_code=303)


def download_story_background(url: str, chapters: int):
    global status
    status["downloading"] = True
    status["message"] = f"Downloading {url}..."
    status["progress"] = "Initializing download..."

    try:
        from novelcast.engine.updater import UpdateEngine
        engine = UpdateEngine(db)
        status["progress"] = "Fetching story information..."
        success, error_msg = engine.download_story(url, chapters)
        if not success:
            logger.error("Background download failed for %s: %s", url, error_msg)
            status["message"] = f"Download failed: {error_msg}"
            status["progress"] = "Failed"
        else:
            status["message"] = "Download completed."
            status["progress"] = "100% - Complete"
    except Exception as e:
        logger.exception("Exception in background download for %s", url)
        status["message"] = f"Download error: {str(e)}"
        status["progress"] = "Error"
    finally:
        status["downloading"] = False


@router.get("/api/status")
def get_status():
    return status


# ─────────────────────────────────────────────
# Subscriptions API
# ─────────────────────────────────────────────

@router.get("/subscriptions")
def subscriptions():
    return db.get_subscriptions()


# ─────────────────────────────────────────────
# Chapter counting (simple heuristic)
# ─────────────────────────────────────────────

@router.get("/get_chapters")
def get_chapters(url: str):
    try:
        request = UrlRequest(url, headers={"User-Agent": "NovelCast/1.0"})

        with urlopen(request, timeout=30) as response:
            content = response.read().decode("utf-8", errors="ignore")

        links = content.count("<a")

        chapters = max(1, min(links, 1000))

        return {"chapters": chapters}

    except Exception as e:
        logger.exception("Error fetching chapters for url=%s", url)
        return {"chapters": 1}


# ─────────────────────────────────────────────
# Cover proxy
# ─────────────────────────────────────────────

@router.get("/cover")
def proxy_cover(url: str):
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()

        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=response.headers.get("content-type", "image/jpeg")
        )

    except Exception as e:
        logger.exception("Error proxying cover url=%s", url)
        placeholder = STATIC_DIR / "images/cover-placeholder.svg"
        return StreamingResponse(
            open(placeholder, "rb"),
            media_type="image/svg+xml"
        )


# ─────────────────────────────────────────────
# Story page
# ─────────────────────────────────────────────

@router.get("/story", response_class=HTMLResponse)
def story(request: Request, url: str):
    sub = db.get_subscription(url)

    if not sub or not sub.get("story_path"):
        logger.error("Story not found for url=%s", url)
        return render_error(request, "Story not found")

    fiction_dir = Path(sub["story_path"])

    if not fiction_dir.exists():
        logger.error("Story folder missing: %s", fiction_dir)
        return render_error(request, "Story folder missing")

    chapters = sorted(fiction_dir.glob("*.html"))
    sort_key = request.query_params.get("sort", DEFAULT_CHAPTER_SORT)
    chapter_names = [c.name for c in chapters]
    chapter_names = sort_chapters(chapter_names, sort_key)

    return templates.TemplateResponse(
        "story.html",
        {
            "request": request,
            "title": sub["title"],
            "author": "Unknown",
            "chapters": chapter_names,
            "url": url,
            "sort": sort_key,
            "sort_options": CHAPTER_SORT_OPTIONS
        }
    )


# ─────────────────────────────────────────────
# Chapter view
# ─────────────────────────────────────────────

@router.get("/chapter", response_class=HTMLResponse)
def chapter(request: Request, url: str, chapter: str):
    sub = db.get_subscription(url)

    if not sub or not sub.get("story_path"):
        logger.error("Story not found for chapter request url=%s chapter=%s", url, chapter)
        return render_error(request, "Story not found")

    story_path = Path(sub["story_path"])
    chapter_file = story_path / chapter

    if not chapter_file.exists():
        logger.error("Chapter not found: %s", chapter_file)
        return render_error(request, "Chapter not found")

    chapters = sorted(story_path.glob("*.html"))
    chapter_names = [c.name for c in chapters]
    current_index = chapter_names.index(chapter) if chapter in chapter_names else -1

    prev_chapter = chapter_names[current_index - 1] if current_index > 0 else None
    next_chapter = chapter_names[current_index + 1] if 0 <= current_index < len(chapter_names) - 1 else None

    html = chapter_file.read_text(encoding="utf-8", errors="ignore")

    return templates.TemplateResponse(
        "chapter.html",
        {
            "request": request,
            "title": sub["title"],
            "author": "Unknown",
            "content": html,
            "url": url,
            "chapter": chapter,
            "prev_chapter": prev_chapter,
            "next_chapter": next_chapter
        }
    )

@router.post("/update_all")
def update_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_all_background)
    return RedirectResponse("/", status_code=303)


def update_all_background():
    global status
    status["downloading"] = True
    status["message"] = "Updating all subscriptions..."
    status["progress"] = "Starting update process..."

    def status_callback(message, progress):
        global status
        status["message"] = message
        status["progress"] = progress

    try:
        from novelcast.engine.updater import UpdateEngine
        engine = UpdateEngine(db)
        engine.check_updates(status_callback)
        status["message"] = "Update completed."
        status["progress"] = "All subscriptions checked"
    except Exception:
        logger.exception("Error running update_all")
        status["message"] = "Update failed."
        status["progress"] = "Error occurred"
    finally:
        status["downloading"] = False