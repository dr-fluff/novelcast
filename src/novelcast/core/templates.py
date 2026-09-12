# novelcast/core/templates.py

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from novelcast.core.template_context import TemplateContext
from novelcast.core.template_names import TemplateNames
from novelcast.utils.link_icons import icon_for_url, link_icon


class AppTemplates(Jinja2Templates):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env.globals["icon_for_url"] = icon_for_url
        self.env.globals["link_icon"] = link_icon
        self.env.globals["TemplateContext"] = TemplateContext
        self.env.globals["TemplateNames"] = TemplateNames

    def TemplateResponse(self, name: str, context: dict, **kwargs) -> HTMLResponse:
        request: Request = context.get("request")
        if request and "current_user" not in context:
            context["current_user"] = getattr(request.state, "user", None)

        if request and "theme" not in context:
            theme = "light"
            try:
                current_user = context.get("current_user")
                settings = request.app.state.ctx.settings
                if current_user:
                    theme = settings.get_user_settings(current_user["id"]).get("theme") or theme
                else:
                    theme = settings.get_resolved_server_settings().get("app", {}).get("theme") or theme
            except (AttributeError, KeyError):
                pass
            context["theme"] = theme if theme in {"system", "light", "dark", "sepia"} else "system"

        return super().TemplateResponse(name, context, **kwargs)
