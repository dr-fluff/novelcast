import logging

logger = logging.getLogger(__name__)


class StoryDownloadService:
    """
    High-level orchestration layer for story downloading.

    Responsibilities:
    - Check if story exists in DB
    - Trigger download engine
    - Ensure DB is updated consistently
    - Keep route layer clean
    """

    def __init__(self, engine, stories_repo, chapters_repo=None):
        self.engine = engine
        self.stories_repo = stories_repo
        self.chapters_repo = chapters_repo

    # -------------------------------------------------
    # MAIN ENTRYPOINT (used by /download/story route)
    # -------------------------------------------------
    def add_story(self, url: str):
        """
        Adds a new story or triggers update if it already exists.
        """

        if not url:
            raise ValueError("URL cannot be empty")

        logger.info(f"Adding story: {url}")

        # 1. check if already exists
        existing = self.stories_repo.get_by_url(url)

        if existing:
            logger.info("Story already exists, triggering update instead")
            return self.update_story(url)

        # 2. download full story via engine
        story_id = self.engine.download_story(url)

        logger.info(f"Story downloaded with id: {story_id}")

        return story_id

    # -------------------------------------------------
    # UPDATE EXISTING STORY
    # -------------------------------------------------
    def update_story(self, url: str):
        """
        Updates an existing story (downloads missing chapters only).
        """

        logger.info(f"Updating story: {url}")

        existing = self.stories_repo.get_by_url(url)

        if not existing:
            logger.warning("Story not found, redirecting to add_story")
            return self.add_story(url)

        story_id = existing["id"]

        # delegate incremental update logic to engine
        result = self.engine.update_story(story_id, url)

        logger.info(f"Update complete: {result}")

        return result

    # -------------------------------------------------
    # OPTIONAL UTILITY METHODS
    # -------------------------------------------------
    def sync_all(self):
        """
        Sync all stories in DB (used by /api/sync/all)
        """
        stories = self.stories_repo.get_all()

        results = []

        for story in stories:
            url = story["source_url"]

            try:
                result = self.update_story(url)
                results.append((url, True, result))
            except Exception as e:
                logger.exception(f"Failed syncing {url}")
                results.append((url, False, str(e)))

        return results