# novelcast/engine/engine_orchestrator.py

import logging

logger = logging.getLogger(__name__)


class StoryDownloadOrchestrator:
    """
    Only responsibility:
    - pick engine
    - fetch raw data
    """

    def __init__(self, selector):
        self.selector = selector

    def download(self, url: str, progress_callback=None) -> dict:
        engine = self.selector.get_engine(url)

        logger.debug("Using engine: %s", engine.__class__.__name__)

        return engine.fetch(url, progress_callback=progress_callback)

    def check_updates(self, url: str) -> dict:
        engine = self.selector.get_engine(url)

        logger.debug("Checking updates with engine: %s", engine.__class__.__name__)

        return engine.check_updates(url)
