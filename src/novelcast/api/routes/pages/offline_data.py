# novcast/api/routes/pages/offline_data.py


from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_templates
from novelcast.core.template_names import TemplateNames
from novelcast.core.template_context import TemplateContext as ContextKey

router = APIRouter()

@router.get("/offline_data")
def offline_data_page(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):

    return templates.TemplateResponse(
            TemplateNames.OFFLINE_DATA,
            {
                ContextKey.REQUEST: request,
                ContextKey.CURRENT_USER: current_user,
            },
        )
