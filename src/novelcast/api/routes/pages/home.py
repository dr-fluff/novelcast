from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from . import router
from novelcast.api.deps import get_stories, get_templates
from novelcast.services import StoryService
from .helpers import filter_stories, sort_stories, story_card


@router.get("/")
def home(
    request: Request,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    query = request.query_params.get("q", "").strip().lower()
    sort = request.query_params.get("sort", "title")

    all_stories = stories.get_all_stories()
    filtered_stories = filter_stories(all_stories, query)
    sorted_stories = sort_stories(filtered_stories, sort)
    cards = [story_card(s) for s in sorted_stories]

    return templates.TemplateResponse("pages/index.html", {
        "request": request,
        "stories": cards,
        "sort": sort,
        "query": query,
        "sort_options": [
            {"key": "title",      "label": "Title"},
            {"key": "author",     "label": "Author"},
            {"key": "downloaded", "label": "Downloaded"},
        ],
    })
