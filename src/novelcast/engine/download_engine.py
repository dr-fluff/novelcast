# novelcast/engine/download_engine.py
import logging

logger = logging.getLogger(__name__)


class DownloadEngine:

    def __init__(self, selector, stories_repo, chapters_repo, sync_repo, file_utils, notifier=None):
        self.notifier = notifier
        self.selector = selector
        self.stories_repo = stories_repo
        self.chapters_repo = chapters_repo
        self.sync_repo = sync_repo
        self.file_utils = file_utils

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def download_story(self, url: str) -> dict:

        engine = self.selector.get_engine(url)

        story_data = engine.download_story(url)

        if not isinstance(story_data, dict):
            raise TypeError(
                f"Engine must return dict, got {type(story_data)}"
            )

        story_id = self._persist_story(story_data)

        self._store_chapters(story_id, story_data.get("chapters", []))

        story_data["story_id"] = story_id
        return story_data

    # -------------------------
    # STORY DB INSERT
    # -------------------------
    def _persist_story(self, story_data: dict) -> int:

        story_id = self.stories_repo.create(
            title=story_data["title"],
            author=story_data.get("author"),
            url=story_data["url"],
        )

        return story_id

    # -------------------------
    # CHAPTER STORAGE
    # -------------------------
    def _store_chapters(self, story_id: int, chapters: list):
        total = len(chapters)

        for i, ch in enumerate(chapters, start=1):
            self.chapters_repo.upsert(
                story_id=story_id,
                chapter_number=ch["number"],
                title=ch.get("title"),
                url=ch.get("url"),
                file_path=ch.get("file_path"),
            )

            if self.notifier:
                self.notifier({
                    "type": "download_progress",
                    "download_id": story_id,
                    "progress": int(i / total * 100),
                    "current": i,
                    "total": total,
                })
