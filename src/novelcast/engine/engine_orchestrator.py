# novelcast/engine/engine_orchestrator.py

import inspect
import logging

logger = logging.getLogger(__name__)


class StoryDownloadOrchestrator:
    def __init__(self, selector):
        self.selector = selector

    def download(self, url: str, progress_callback=None, story_match: str | None = None) -> dict:
        engine = self.selector.get_engine(url)
        logger.debug("Using engine: %s", engine.__class__.__name__)

        kwargs = {"progress_callback": progress_callback}
        if story_match and "story_match" in inspect.signature(engine.fetch).parameters:
            kwargs["story_match"] = story_match

        return engine.fetch(url, **kwargs)

    def check_updates(self, url: str, story_match: str | None = None) -> dict:
        engine = self.selector.get_engine(url)
        logger.debug("Checking updates with engine: %s", engine.__class__.__name__)

        kwargs = {}
        if story_match and "story_match" in inspect.signature(engine.check_updates).parameters:
            kwargs["story_match"] = story_match

        return engine.check_updates(url, **kwargs)
