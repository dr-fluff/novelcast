# novcast/api/routes/pages/offline_data.py


from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_templates

router = APIRouter()

@router.get("/offline_data")
def offline_data_page(
    request: Request,
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):

    return templates.TemplateResponse(
            "pages/offline_data.html",
            {
                "request": request,
                "current_user": current_user,
            },
        )
