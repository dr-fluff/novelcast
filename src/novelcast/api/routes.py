from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.storage.db import Database
from novelcast.engine.updater import UpdateEngine

from pathlib import Path
from urllib.parse import urlparse, urljoin, quote
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup
import requests
import logging

router = APIRouter()

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
    subs_raw = db.get_subscriptions()
    subs = [enrich_subscription(s) for s in subs_raw]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "subs": subs
        }
    )


# ─────────────────────────────────────────────
# Subscribe
# ─────────────────────────────────────────────

@router.post("/subscribe")
def subscribe(url: str = Form(...), chapters: int = Form(1)):
    print(f"Subscribing to {url} ({chapters} chapters)")

    existing = db.get_subscription(url)

    if not existing:
        db.add_subscription(url, title=url)

    success, error_msg = engine.download_story(url, chapters)

    if not success:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": {},   # OK for now, but can be improved later
                "error": error_msg
            }
        )

    return RedirectResponse("/", status_code=303)


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
        print(f"Error fetching chapters: {e}")
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

    except Exception:
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
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Story not found"}
        )

    fiction_dir = Path(sub["story_path"])

    if not fiction_dir.exists():
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Story folder missing"}
        )

    chapters = sorted(fiction_dir.glob("*.html"))

    return templates.TemplateResponse(
        "story.html",
        {
            "request": request,
            "title": sub["title"],
            "author": "Unknown",
            "chapters": [c.name for c in chapters],
            "url": url
        }
    )


# ─────────────────────────────────────────────
# Chapter view
# ─────────────────────────────────────────────

@router.get("/chapter", response_class=HTMLResponse)
def chapter(request: Request, url: str, chapter: str):
    sub = db.get_subscription(url)

    if not sub or not sub.get("story_path"):
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Story not found"}
        )

    chapter_file = Path(sub["story_path"]) / chapter

    if not chapter_file.exists():
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Chapter not found"}
        )

    html = chapter_file.read_text(encoding="utf-8", errors="ignore")

    return templates.TemplateResponse(
        "chapter.html",
        {
            "request": request,
            "title": sub["title"],
            "author": "Unknown",
            "content": html,
            "url": url,
            "chapter": chapter
        }
    )

@router.post("/update_all")
def update_all():
    from novelcast.engine.updater import UpdateEngine

    engine = UpdateEngine(db)
    engine.check_updates()

    return RedirectResponse("/", status_code=303)