# novelcast/core/templates.py

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


class AppTemplates(Jinja2Templates):
    def TemplateResponse(self, name: str, context: dict, **kwargs) -> HTMLResponse:
        request: Request = context.get("request")
        if request and "current_user" not in context:
            context["current_user"] = getattr(request.state, "user", None)
        return super().TemplateResponse(name, context, **kwargs)
