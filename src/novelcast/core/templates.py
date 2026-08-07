# novelcast/core/templates.py

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from novelcast.utils.link_icons import icon_for_url, link_icon


class AppTemplates(Jinja2Templates):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env.globals["icon_for_url"] = icon_for_url
        self.env.globals["link_icon"] = link_icon

    def TemplateResponse(self, name: str, context: dict, **kwargs) -> HTMLResponse:
        request: Request = context.get("request")
        if request and "current_user" not in context:
            context["current_user"] = getattr(request.state, "user", None)
        return super().TemplateResponse(name, context, **kwargs)