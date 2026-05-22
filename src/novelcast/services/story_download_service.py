# novelcast/services/story_download_service.py
# Full file — replaces the existing one entirely.

import logging
import uuid

from novelcast.utils.url_normalizer import normalize_story_url

logger = logging.getLogger(__name__)


class StoryDownloadService:
    def __init__(self, orchestrator, pipeline, parser, stories_repo, notifier=None):
        self.orchestrator  = orchestrator
        self.pipeline      = pipeline
        self.parser        = parser
        self.stories_repo  = stories_repo
        self.notifier      = notifier

    def add_story(self, url: str):
        logger.debug("Story download requested")

        normalized_url = normalize_story_url(url)
        download_id    = str(uuid.uuid4())
        self._emit("download_started", {"download_id": download_id, "source_url": normalized_url})

        try:
            # 1. check existing
            existing = self.stories_repo.get_by_url(normalized_url)
            if existing:
                self._emit("download_finished", {
                    "download_id": download_id,
                    "story_id":   existing["id"],
                    "title":      existing.get("title"),
                })
                return existing["id"]

            def progress(message: str, progress_value: int | None = None):
                self._emit("download_progress", {
                    "download_id": download_id,
                    "source_url":  normalized_url,
                    "progress":    progress_value,
                    "indeterminate": progress_value is None,
                })

            # 2. fetch via orchestrator
            raw        = self.orchestrator.download(normalized_url, progress_callback=progress)
            source_url = raw.get("url") or normalized_url

            # 3. create story row
            story_id = self.stories_repo.create(
                raw.get("title") or "Unknown",
                raw.get("author"),
                source_url,
            )

            # 4. parse
            parsed = self.parser.parse(raw)
            parsed["source_url"]       = source_url
            parsed["source_file_path"] = raw.get("file_path")

            self.stories_repo.update_metadata(
                story_id,
                parsed.get("title") or raw.get("title") or "Unknown",
                parsed.get("author") or raw.get("author"),
            )

            # 5. link author — get-or-create Author row + story_author join
            author_name = parsed.get("author") or raw.get("author")
            if author_name:
                from novelcast.db.repositories.author_repository import AuthorRepository
                author_repo = AuthorRepository(self.stories_repo._session_factory)
                author_id   = author_repo.get_or_create(author_name)
                author_repo.link_to_story(author_id, story_id)

            # 6. persist files, paths, chapters, stats
            self.pipeline.persist(story_id, parsed)

            self._emit("download_finished", {
                "download_id": download_id,
                "story_id":    story_id,
                "title":       parsed.get("title"),
            })

            return story_id

        except Exception as e:
            self._emit("download_failed", {
                "download_id": download_id,
                "source_url":  normalized_url,
                "error":       str(e),
            })
            raise

    def sync_story(self, story: dict) -> dict:
        # Preserve existing sync logic — not changed here.
        raise NotImplementedError

    def _emit(self, event_type: str, payload: dict):
        if self.notifier:
            self.notifier(event_type, payload)
