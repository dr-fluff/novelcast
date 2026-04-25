import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StoryDownloadService:

    def __init__(self, selector, parser, pipeline):
        self.selector = selector
        self.parser = parser
        self.pipeline = pipeline

    def add_story(self, url: str):

        engine = self.selector.get_engine(url)

        raw = engine.download_story(url)

        parsed = self.parser.parse(raw)

        story_id = self.pipeline.persist(parsed)

        return story_id