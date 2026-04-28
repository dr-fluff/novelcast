import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StoryDownloadService:
    def __init__(self, selector, parser, pipeline):
        self.selector = selector
        self.parser = parser
        self.pipeline = pipeline

    def add_story(self, url: str):
        logger.info("Starting story download", extra={"url": url})
        
        try:
            engine = self.selector.get_engine(url)
            logger.debug(f"Selected engine: {engine.__class__.__name__}", extra={"url": url})
            
            raw = engine.fetch(url)
            logger.debug(f"Raw data fetched: {list(raw.keys())}", extra={"url": url})

            parsed = self.parser.parse(raw)
            parsed["source_url"] = raw.get("url")
            parsed["source_file_path"] = raw.get("file_path")
            logger.debug(f"Parsed story data: title={parsed.get('title')}, author={parsed.get('author')}", extra={"url": url})

            story_id = self.pipeline.persist(parsed)
            logger.debug(f"Story persisted with ID: {story_id}", extra={"url": url})

            return story_id
        except Exception as e:
            logger.error("Error during story download", exc_info=e, extra={"url": url})
            raise RuntimeError(f"Failed to download story: {str(e)}") from e