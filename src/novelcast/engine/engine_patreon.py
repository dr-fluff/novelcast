# novelcast/engine/engine_patreon.py
import logging
from urllib.parse import urlparse

from .base import StoryEngine

logger = logging.getLogger(__name__)
PATREON_SUPPORTED_LINKS = {"patreon.com", "www.patreon.com"}

class PatreonEngine(StoryEngine):

    def __init__(self, settings_repo, patreon_config):
        self.settings_repo = settings_repo
        self.config = patreon_config

    # -------------------------
    # ROUTING
    # -------------------------
    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in PATREON_SUPPORTED_LINKS if hostname else False

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        logger.error("Patreon engine not implemented: %s", url)
        raise NotImplementedError("Patreon engine is not implemented yet")
    

    def check_updates(self, url: str) -> dict:
        logger.error("Patreon engine not implemented: %s", url)
        raise NotImplementedError("Patreon engine is not implemented yet")
    
    
    def _emit_progress(self, message: str, progress_callback=None, value: int = 0):
        if progress_callback:
            progress_callback(message, value)
            logger.debug("Progress: %s (%d%%)", message, value)
    
