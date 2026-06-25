# novelcast/services/notification_service.py

import asyncio
import logging

logger = logging.getLogger(__name__)


class NotifierService:
    def __init__(self, ws_manager=None):
        self.ws_manager = ws_manager

    def broadcast(self, event_type: str, payload: dict) -> None:
        if not self.ws_manager:
            return
        try:
            asyncio.ensure_future(self.ws_manager.broadcast(event_type, payload))
        except RuntimeError:
            logger.warning("WS broadcast skipped — no running event loop")

    async def broadcast_async(self, event_type: str, payload: dict) -> None:
        if not self.ws_manager:
            return
        try:
            await self.ws_manager.broadcast(event_type, payload)
        except Exception:
            logger.warning("WS broadcast_async failed", exc_info=True)