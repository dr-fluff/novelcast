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

        if request and "reading_settings_schema" not in context:
            try:
                context["reading_settings_schema"] = request.app.state.ctx.settings.get_reading_settings_schema()
            except (AttributeError, KeyError):
                context["reading_settings_schema"] = {}

        if request and "theme" not in context:
            theme = "system"
            try:
                current_user = context.get("current_user")
                settings = request.app.state.ctx.settings
                if current_user:
                    device_id = request.cookies.get("nc_device_id")
                    user_settings = settings.get_user_settings(current_user["id"], device_id=device_id)
                    theme = user_settings.get("chapter_theme") or theme
            except (AttributeError, KeyError):
                pass
            context["theme"] = theme if theme in {"system", "light", "dark", "sepia"} else "system"

        return super().TemplateResponse(name, context, **kwargs)
