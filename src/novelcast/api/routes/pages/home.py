from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from . import router
from novelcast.api.deps import get_current_user, get_progress, get_stories, get_templates
from novelcast.services import ProgressService, StoryService
from .helpers import (
    enrich_story_progress,
    filter_stories,
    sort_stories,
    story_card,
    story_filter_options,
)


@router.get("/")
def home(
    request: Request,
    stories: StoryService = Depends(get_stories),
    progress: ProgressService = Depends(get_progress),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    query = request.query_params.get("q", "").strip().lower()
    sort = request.query_params.get("sort", "title")
    genre = request.query_params.get("genre", "").strip()
    tag = request.query_params.get("tag", "").strip()
    series = request.query_params.get("series", "").strip()
    language = request.query_params.get("language", "").strip()
    status = request.query_params.get("status", "").strip()

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
    )
    sorted_stories = sort_stories(filtered_stories, sort)
    cards = [story_card(s) for s in sorted_stories]

    return templates.TemplateResponse("pages/index.html", {
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
            {"key": "title",      "label": "Title"},
            {"key": "author",     "label": "Author"},
            {"key": "series",     "label": "Series"},
            {"key": "downloaded", "label": "Downloaded"},
            {"key": "unread",     "label": "Unread first"},
            {"key": "updated",    "label": "Last updated"},
            {"key": "created",    "label": "Date added"},
            {"key": "year",       "label": "Publish year"},
        ],
        "status_options": [
            {"key": "",            "label": "Any status"},
            {"key": "unread",      "label": "Has unread chapters"},
            {"key": "read",        "label": "All downloaded read"},
            {"key": "not_started", "label": "Not started"},
        ],
    })
