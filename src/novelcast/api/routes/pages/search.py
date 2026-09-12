# novelcast/api/routes/pages/search.py

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_settings, get_templates
from novelcast.core.template_names import TemplateNames
from novelcast.core.template_context import TemplateContext as ContextKey
from novelcast.services.scrapers import scrape_all, scrape_details
from novelcast.services.search_service import SearchService
from novelcast.services.settings_service import SettingsService

router = APIRouter()


@router.get("/search")
def search_page(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse(
        TemplateNames.SEARCH,
        {
            ContextKey.REQUEST: request,
            ContextKey.CURRENT_USER: current_user,
        },
    )


@router.get("/search/results")
async def search_results(
    request: Request,
    q: str = "",
    templates: Jinja2Templates = Depends(get_templates),
    settings_service: SettingsService = Depends(get_settings),
):
    q = q.strip()

    if not q:
        return templates.TemplateResponse(
            TemplateNames.SEARCH_RESULTS,
            {
                ContextKey.REQUEST: request,
                ContextKey.QUERY: None,
                ContextKey.PARSED: None,
                ContextKey.RESULTS: [],
                "error": None,
            },
        )

    search_service = SearchService(settings_service=settings_service)

    try:
        parsed = search_service.parse_query(q)
        search_urls = search_service.build_search_urls(parsed)

        if parsed.target in ("fiction", "author") and parsed.lookup_type in (
            "id",
            "url",
        ):
            results = await scrape_details(search_urls, settings_service=settings_service)
        else:
            results = await scrape_all(search_urls, settings_service=settings_service)

        error = None
    except ValueError as e:
        parsed = None
        search_urls = []
        results = []
        error = str(e)

    return templates.TemplateResponse(
        TemplateNames.SEARCH_RESULTS,
        {
            ContextKey.REQUEST: request,
            ContextKey.QUERY: q,
            ContextKey.PARSED: parsed,
            ContextKey.SEARCH_URLS: search_urls,
            ContextKey.RESULTS: results,
            "error": error,
        },
    )
