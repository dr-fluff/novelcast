from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_stories, get_templates
from novelcast.services import StoryService

router = APIRouter()


@router.get("/authors")
def authors(
    request: Request,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    query = request.query_params.get("q", "").strip().lower()
    sort = request.query_params.get("sort", "name")

    all_authors = stories.get_all_authors(query=query, sort=sort)

    return templates.TemplateResponse(
        "pages/authors.html",
        {
            "request": request,
            "authors": all_authors,
            "query": query,
            "sort": sort,
            "sort_options": [
                {"key": "name", "label": "Name (A–Z)"},
                {"key": "stories", "label": "Most stories"},
                {"key": "updated", "label": "Last updated"},
                {"key": "added", "label": "Date added"},
            ],
        },
    )


@router.get("/authors/{author_id}")
def author_detail(
    request: Request,
    author_id: int,
    stories: StoryService = Depends(get_stories),
    templates: Jinja2Templates = Depends(get_templates),
):
    author = stories.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    return templates.TemplateResponse(
        "pages/author_detail.html",
        {
            "request": request,
            "author": author,
        },
    )
