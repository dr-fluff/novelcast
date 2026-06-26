# novelcast/api/routes/admin/log_tail.py

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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