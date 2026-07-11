# novelcast/api/routes/pages/home.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import (
    get_current_user,
    get_progress,
    get_settings,
    get_stories,
    get_templates,
)
from novelcast.services import ProgressService, SettingsService, StoryService

from .helpers import (
    enrich_story_progress,
    filter_stories,
    sort_stories,
    story_card,
    story_filter_options,
)
from .preferences import device_preference_key

router = APIRouter()


@router.get("/")
def home(
    request: Request,
    stories: StoryService = Depends(get_stories),
    progress: ProgressService = Depends(get_progress),
    settings: SettingsService = Depends(get_settings),  # ← new
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    preference_key = None
    device_id = request.cookies.get("novelcast_device_id")
    if current_user and device_id:
        preference_key = device_preference_key(device_id, "library.index")

    if request.query_params.get("clear_library_preferences") == "1":
        if current_user and preference_key:
            settings.delete_user_preference(current_user["id"], preference_key)
        return RedirectResponse("/", status_code=303)

    saved_preferences = {}
    has_query_state = any(
        key in request.query_params for key in ("q", "sort", "genre", "tag", "series", "language", "status")
    )
    if current_user and preference_key and not has_query_state:
        saved = settings.get_user_preference(current_user["id"], preference_key, {})
        if isinstance(saved, dict):
            saved_preferences = saved

    query = request.query_params.get("q", saved_preferences.get("q", "")).strip().lower()
    sort = request.query_params.get("sort", saved_preferences.get("sort", "title"))
    genre = request.query_params.get("genre", saved_preferences.get("genre", "")).strip()
    tag = request.query_params.get("tag", saved_preferences.get("tag", "")).strip()
    series = request.query_params.get("series", saved_preferences.get("series", "")).strip()
    language = request.query_params.get("language", saved_preferences.get("language", "")).strip()
    status = request.query_params.get("status", saved_preferences.get("status", "")).strip()

    # Parse ignore_prefixes from settings
    raw_prefixes = settings.get_server_setting("library.ignore_prefixes", default="the,a,an")
    ignore_prefixes = [p.strip() for p in raw_prefixes.split(",") if p.strip()]

    all_stories = stories.get_all_stories()
    filter_options = story_filter_options(all_stories)
    progress_rows = progress.get_all_for_user(current_user["id"]) if current_user else []
    all_stories = enrich_story_progress(all_stories, progress_rows)
    filtered_stories = filter_stories(
        all_stories,
        query,
        genre=genre,
        tag=tag,
        series=series,
        language=language,
        status=status,
        ignore_prefixes=ignore_prefixes,
    )
    sorted_stories = sort_stories(
        filtered_stories,
        sort,
        ignore_prefixes=ignore_prefixes,
    )
    cards = [story_card(s) for s in sorted_stories]

    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "stories": cards,
            "sort": sort,
            "query": query,
            "genre": genre,
            "tag": tag,
            "series": series,
            "language": language,
            "status": status,
            "filter_options": filter_options,
            "sort_options": [
                {"key": "title", "label": "Title"},
                {"key": "author", "label": "Author"},
                {"key": "series", "label": "Series"},
                {"key": "downloaded", "label": "Downloaded"},
                {"key": "unread", "label": "Unread first"},
                {"key": "updated", "label": "Last updated"},
                {"key": "created", "label": "Date added"},
                {"key": "year", "label": "Publish year"},
            ],
            "status_options": [
                {"key": "", "label": "Any status"},
                {"key": "unread", "label": "Has unread chapters"},
                {"key": "no_unread", "label": "Hav no unread chapters"},
                {"key": "read", "label": "All downloaded read"},
                {"key": "not_started", "label": "Not started"},
            ],
        },
    )
