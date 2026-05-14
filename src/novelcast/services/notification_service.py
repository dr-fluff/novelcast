# novelcast/services/notification_service.py

import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class NotifierService:
    def __init__(self, ws_manager=None):
        self.ws_manager = ws_manager

    def broadcast(self, payload: dict) -> None:
        if not self.ws_manager:
            return

        try:
            import anyio
            anyio.from_thread.run(self.ws_manager.broadcast, payload)
        except Exception:
            logger.warning("WS broadcast failed", exc_info=True)

    async def broadcast_async(self, payload: dict) -> None:
        if not self.ws_manager:
            return

        try:
            await self.ws_manager.broadcast(payload)
        except Exception:
            logger.warning("WS broadcast_async failed", exc_info=True)