# novelcast/api/routes/pages/search.py

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_templates
from novelcast.services.search_service import SearchService
from novelcast.services.scrapers import scrape_all, scrape_details

search_service = SearchService()

from fastapi import APIRouter

router = APIRouter()


@router.get("/search")
def search_page(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse("pages/search.html", {
        "request": request,
        "current_user": current_user,
    })


@router.get("/search/results")
async def search_results(
    request: Request,
    q: str = "",
    templates: Jinja2Templates = Depends(get_templates),
):
    q = q.strip()

    if not q:
        return templates.TemplateResponse("partials/search_results.html", {
            "request": request,
            "query": None,
            "parsed": None,
            "results": [],
            "error": None,
        })

    try:
        parsed = search_service.parse_query(q)
        search_urls = search_service.build_search_urls(parsed)

        if parsed.target in ("fiction", "author") and parsed.lookup_type in ("id", "url"):
            results = await scrape_details(search_urls)
        else:
            results = await scrape_all(search_urls)

        error = None
    except ValueError as e:
        parsed = None
        search_urls = []
        results = []
        error = str(e)

    return templates.TemplateResponse("partials/search_results.html", {
        "request": request,
        "query": q,
        "parsed": parsed,
        "search_urls": search_urls,
        "results": results,
        "error": error,
    })