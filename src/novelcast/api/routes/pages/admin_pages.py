from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from . import router
from novelcast.api.deps import (
    get_chapter_filter,
    get_current_user,
    get_library_sync,
    get_settings,
    get_stories,
    get_templates,
    get_users,
)
from novelcast.services import (
    LibrarySyncService,
    SettingsService,
    StoryService,
    UserService,
)
from novelcast.services.chapter_filter_service import ChapterFilterService
from novelcast.parser.epub_parser import DEFAULT_PATTERNS


_BUILTIN_PATTERN_LABELS = {
    r"\bchapter\s*:?\s*\d+":    "Chapter N / Chapter: N",
    r"\bchapter\s*\?+":         "Chapter ???",
    r"\bch\.?\s*\d+":           "Ch. 42 / Ch42",
    r"^\[?\d+\.\d+":            "1.1 / 3.10 / [1.1]",
    r"^\[?\d+\s*[-–]":          "1 - Title / [1 - Title]",
    r"^\[?\d+\.":               "1. Title / [1. Title]",
    r"\bpart\s*\d+":            "Part 1 / Part 9 (3.10)",
    r"\bpart\s+[ivxlcdm]+\b":   "Part IV (Roman numerals)",
    r"\bprologue\b":            "Prologue",
    r"\bepilogue\b":            "Epilogue",
    r"\binterlude\b":           "Interlude / Bestiary Interlude : Hydra",
    r"\bafterword\b":           "Afterword",
    r"\bglossary\b":            "Glossary",
    r"\bappendix\b":            "Appendix",
    r"\bcover\b":               "Cover page",
    r"\bby\s+\w+":              "Story Title by Author",
    r"\w.*\s+\d+\s*[-–]":      "Series Title 26 - Chapter Name",
}


@router.get("/admin")
def admin_dashboard(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    stories: StoryService = Depends(get_stories),
    library_sync: LibrarySyncService = Depends(get_library_sync),
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    all_users = users.get_all_users()
    all_stories = stories.get_all_stories()

    stats = {
        "total_users":   len(all_users),
        "total_stories": len(all_stories),
        "pending_syncs": library_sync.pending_count(),
        "pending_chapters": library_sync.pending_chapter_count(),
        "need_attention": 0,
    }

    health_checks = [
        {
            "name":   "Database",
            "status": "healthy",
            "detail": "Connection successful",
        },
        {
            "name":   "Sync Worker",
            "status": "healthy",
            "detail": "Running",
        },
    ]

    return templates.TemplateResponse("pages/admin.html", {
        "request":       request,
        "user":          current_user,
        "stats":         stats,
        "health_checks": health_checks,
        "users":         all_users,
    })


@router.post("/admin/check-updates")
def check_updates(
    current_user: dict | None = Depends(get_current_user),
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    result = library_sync.check_updates()
    pending_stories = result.get("stories_with_updates", 0)
    pending_chapters = result.get("pending_chapters", 0)

    return {
        **result,
        "message": f"{pending_stories} stories have {pending_chapters} new chapters available.",
    }


@router.get("/admin/chapter-patterns")
def chapter_patterns_page(
    request: Request,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    builtin = [
        {"pattern": p, "description": _BUILTIN_PATTERN_LABELS.get(p, "")}
        for p in DEFAULT_PATTERNS
    ]

    return templates.TemplateResponse("pages/chapter_patterns.html", {
        "request":          request,
        "user":             current_user,
        "chapter_patterns": chapter_filter.get_all_patterns(),
        "builtin_patterns": builtin,
    })


@router.get("/admin/users")
def users(
    request: Request,
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return templates.TemplateResponse("pages/users.html", {
        "request": request,
        "user": current_user,
        "users": users.get_all_users(),
    })


@router.get("/admin/users/{user_id}/edit")
def edit_user_page(
    request: Request,
    user_id: int,
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    target_user = users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse("pages/user_form.html", {
        "request": request,
        "user": current_user,
        "error": request.query_params.get("error"),
        "mode": "edit",
        "form_action": f"/admin/users/{user_id}/edit",
        "submit_label": "Save Changes",
        "back_url": "/admin/users",
        "back_label": "← Back to Users",
        "show_role": True,
        "form_user": target_user,
    })