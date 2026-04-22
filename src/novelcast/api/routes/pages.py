# api/routes/pages.py

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from novelcast.api.deps import require_user

router = APIRouter()

def templates(request: Request):
    return request.app.state.templates


def render(request: Request, template: str, context: dict, status_code: int = 200):
    return templates(request).TemplateResponse(
        template,
        {"request": request, **context},
        status_code=status_code,
    )


def render_error(request: Request, message: str, status_code: int = 404):
    return render(request, "pages/error.html", {"error_message": message}, status_code)


# ─────────────────────────────
# Pages
# ─────────────────────────────
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    qm = request.app.state.qm

    sort_key = request.query_params.get("sort", "title")

    subs_raw = qm.fetchall("subscriptions.get_dashboard", ())

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

    return request.app.state.templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "subs": subs,
            "sort": sort_key,
        },
    )

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return render(request, "pages/login.html", {})


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user=Depends(require_user)):
    return render(request, "pages/admin.html", {"user": user})


@router.get("/story", response_class=HTMLResponse)
def story(request: Request, url: str):
    sub, chapters = pages(request).get_story(url)

    if not sub:
        return render_error(request, "Story not found", 404)

    return render(request, "pages/story.html", {
        "title": sub.get("title"),
        "chapters": chapters,
        "url": url,
    })


@router.get("/chapter", response_class=HTMLResponse)
def chapter(request: Request, url: str, chapter: str):
    sub, html, error = pages(request).get_chapter(url, chapter)

    if error:
        return render_error(request, error, 404)

    return render(request, "pages/chapter.html", {
        "title": sub.get("title"),
        "content": html,
        "chapter": chapter,
    })


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return render(request, "pages/settings.html", {})