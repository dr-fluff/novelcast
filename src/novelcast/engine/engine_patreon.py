import logging
from urllib.parse import urlparse

from .base import StoryEngine

logger = logging.getLogger(__name__)


class PatreonEngine(StoryEngine):

    def __init__(self, settings_repo, patreon_config):
        self.settings_repo = settings_repo
        self.config = patreon_config

    # -------------------------
    # ROUTING
    # -------------------------
    def can_handle(self, url: str) -> bool:
        return urlparse(url).hostname in {"patreon.com", "www.patreon.com"}

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        logger.error("Patreon engine not implemented: %s", url)
        raise NotImplementedError("Patreon engine is not implemented yet")
