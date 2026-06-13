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
    get_health_check,
)

from novelcast.services import (
    LibrarySyncService,
    SettingsService,
    StoryService,
    UserService,
    HealthCheckService,
    ChapterFilterService,
)
from novelcast.core.defaults import DEFAULT_CHAPTER_PATTERNS

@router.get("/admin")
def admin_dashboard(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    stories: StoryService = Depends(get_stories),
    library_sync: LibrarySyncService = Depends(get_library_sync),
    users: UserService = Depends(get_users),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
    health_svc: HealthCheckService = Depends(get_health_check),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    all_users   = users.get_all_users()
    all_stories = stories.get_all_stories()
    pending     = library_sync.pending_count()

    stats = {
        "total_users":      len(all_users),
        "total_stories":    len(all_stories),
        "pending_syncs":    pending,
        "pending_chapters": library_sync.pending_chapter_count(),
        "need_attention":   0,
    }

    health_checks = [r.as_dict() for r in health_svc.run_all(pending_syncs=pending)]

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


@router.get("/admin/users/{user_id}/delete")
def delete_user(
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
    
    return 

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
    
# Add these endpoints to novelcast/api/routes/pages/admin_pages.py

from pydantic import BaseModel


class PatternRequest(BaseModel):
    pattern: str
    description: str = ""


class PatternTestRequest(BaseModel):
    pattern: str
    samples: list[str]


class PatternUpdateRequest(BaseModel):
    enabled: bool | None = None


@router.get("/admin/chapter-patterns")
def chapter_patterns_page(
    request: Request,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all patterns from DB (builtin + custom)
    all_patterns = chapter_filter.get_all_patterns()

    return templates.TemplateResponse("pages/chapter_patterns.html", {
        "request": request,
        "user": current_user,
        "chapter_patterns": all_patterns,
    })

@router.post("/admin/chapter-patterns")
def create_pattern(
    req: PatternRequest,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = chapter_filter.add_pattern(req.pattern, req.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/chapter-patterns/test")
def test_pattern(
    req: PatternTestRequest,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        results = chapter_filter.test_pattern(req.pattern, req.samples)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/admin/chapter-patterns/{pattern_id}")
def update_pattern(
    pattern_id: int,
    req: PatternUpdateRequest,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if req.enabled is not None:
        chapter_filter.set_enabled(pattern_id, req.enabled)
    
    return {"success": True}


@router.delete("/admin/chapter-patterns/{pattern_id}")
def delete_pattern(
    pattern_id: int,
    chapter_filter: ChapterFilterService = Depends(get_chapter_filter),
    current_user: dict | None = Depends(get_current_user),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        chapter_filter.delete_pattern(pattern_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))