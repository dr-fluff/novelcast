# novelcast/api/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from novelcast.api.deps import get_current_user, get_users, get_chapter_filter
from novelcast.services import UserService
from novelcast.services.chapter_filter_service import ChapterFilterService


router = APIRouter(tags=["admin"])


def _require_admin(current_user: dict | None = Depends(get_current_user)) -> dict:
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Users ──────────────────────────────────────────────────────────────────

@router.post("/users/{user_id}/promote")
def promote_user(
    user_id: int,
    current_user: dict | None = Depends(get_current_user),
    users: UserService = Depends(get_users),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")
    users.promote_to_admin(user_id)
    return RedirectResponse("/settings?success=1", status_code=303)


# ── Chapter patterns API ───────────────────────────────────────────────────

class PatternCreate(BaseModel):
    pattern: str
    description: str = ""

class PatternPatch(BaseModel):
    enabled: bool | None = None
    pattern: str | None = None
    description: str | None = None

class PatternTest(BaseModel):
    pattern: str
    samples: list[str]


@router.get("/chapter-patterns")
def list_patterns(
    _user: dict = Depends(_require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    return svc.get_all_patterns()


@router.post("/chapter-patterns", status_code=201)
def create_pattern(
    body: PatternCreate,
    _user: dict = Depends(_require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    try:
        return svc.add_pattern(body.pattern, body.description)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/chapter-patterns/{pattern_id}")
def patch_pattern(
    pattern_id: int,
    body: PatternPatch,
    _user: dict = Depends(_require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    if body.enabled is not None:
        svc.set_enabled(pattern_id, body.enabled)

    if body.pattern is not None or body.description is not None:
        existing = svc.get_all_patterns()
        row = next((p for p in existing if p["id"] == pattern_id), None)
        if not row:
            raise HTTPException(status_code=404, detail="Pattern not found")
        try:
            svc.update_pattern(
                pattern_id,
                body.pattern or row["pattern"],
                body.description if body.description is not None else row["description"],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    return {"ok": True}


@router.delete("/chapter-patterns/{pattern_id}", status_code=204)
def delete_pattern(
    pattern_id: int,
    _user: dict = Depends(_require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    svc.delete_pattern(pattern_id)


@router.post("/chapter-patterns/test")
def test_pattern(
    body: PatternTest,
    _user: dict = Depends(_require_admin),
    svc: ChapterFilterService = Depends(get_chapter_filter),
):
    try:
        return svc.test_pattern(body.pattern, body.samples)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))