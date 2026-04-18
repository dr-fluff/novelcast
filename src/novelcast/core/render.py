from fastapi import Request
from novelcast.core.context import build_global_context

def render(request: Request, template: str, context: dict = None):
    context = context or {}

    global_context = build_global_context(request)

    merged = {
        **global_context,
        **context
    }

    return request.app.state.templates.TemplateResponse(
        template,
        merged
    )