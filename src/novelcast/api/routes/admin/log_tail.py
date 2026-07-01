# novelcast/api/routes/admin/log_tail.py

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, APIRouter

from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_settings, get_templates, get_logs
from novelcast.services import LoggingService

router = APIRouter()
logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.5   # seconds


@router.websocket("/admin/logs/tail")
async def log_tail_ws(websocket: WebSocket):
    
    await websocket.accept()

    # Import the singleton buffer — already populated since startup
    from novelcast.core.logging import log_buffer

    # Send backlog so the page isn't empty on load
    backlog, cursor = log_buffer.drain()
    if backlog:
        await websocket.send_json({"type": "backlog", "lines": backlog})

    try:
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            new_lines, cursor = log_buffer.drain(cursor)
            if new_lines:
                await websocket.send_json({"type": "lines", "lines": new_lines})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("log_tail_ws error")
    
    
@router.get("/logs")
def logs(
    request: Request,
    settings: SettingsService = Depends(get_settings),
    loggers: LoggingService = Depends(get_logs),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse("pages/index.html", {})