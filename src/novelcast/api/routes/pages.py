from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


def render(request: Request, template: str, context: dict):
    return request.app.state.templates.TemplateResponse(
        template,
        {"request": request, **context},
    )


@router.get("/")
def home(request: Request):
    ctx = request.app.state.ctx

    stories = ctx.stories.get_all_stories()

    return render(
        request,
        "pages/index.html",
        {"stories": stories},
    )