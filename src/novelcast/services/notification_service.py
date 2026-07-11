# novelcast/services/notification_service.py

import asyncio
import logging

logger = logging.getLogger(__name__)


class NotifierService:
    def __init__(self, ws_manager=None, loop=None):
        self.ws_manager = ws_manager
        self.loop = loop

    def broadcast(self, event_type: str, payload: dict) -> None:
        if not self.ws_manager:
            return

        if self.loop and self.loop.is_running():
            # safest cross-thread call
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.broadcast(event_type, payload),
                self.loop,
            )
        else:
            logger.warning("No event loop available for WS broadcast")
