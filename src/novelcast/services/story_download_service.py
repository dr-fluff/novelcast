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
        story_id = story.get("id")
        source_url = story.get("source_url")
        if not story_id or not source_url:
            return {"story_id": story_id, "new_chapters": 0, "skipped": True}

        logger.info("Syncing story", extra={"story_id": story_id, "source_url": source_url})

        raw = self.orchestrator.download(source_url)
        parsed = self.parser.parse(raw)
        parsed["source_url"] = raw.get("url") or source_url
        parsed["source_file_path"] = raw.get("file_path")

        self.stories_repo.update_metadata(
            story_id,
            parsed.get("title") or story.get("title") or "Unknown",
            parsed.get("author") or story.get("author"),
        )

        new_chapters = self.pipeline.append_new_chapters(story_id, parsed)

        if new_chapters:
            self._emit("sync_story_updated", {
                "story_id": story_id,
                "title": parsed.get("title") or story.get("title"),
                "new_chapters": len(new_chapters),
            })

        return {
            "story_id": story_id,
            "new_chapters": len(new_chapters),
            "chapter_numbers": new_chapters,
        }

    def check_story_updates(self, story: dict) -> dict:
        story_id = story.get("id")
        source_url = story.get("source_url")
        if not story_id or not source_url:
            return {"story_id": story_id, "pending_chapters": 0, "chapter_numbers": [], "skipped": True}

        raw = self.orchestrator.check_updates(source_url)
        online_numbers = self._online_chapter_numbers(raw)
        local_numbers = self.pipeline.chapters_repo.get_chapter_numbers(story_id)
        pending = sorted(number for number in online_numbers if number not in local_numbers)

        return {
            "story_id": story_id,
            "title": raw.get("title") or story.get("title"),
            "pending_chapters": len(pending),
            "chapter_numbers": pending,
            "online_chapters": len(online_numbers),
            "local_chapters": len(local_numbers),
        }

    def _online_chapter_numbers(self, raw: dict) -> list[int]:
        chapters = raw.get("chapters") or raw.get("raw", {}).get("chapters")
        chapters = chapters or raw.get("zchapters") or raw.get("raw", {}).get("zchapters")

        if chapters:
            return list(range(1, len(chapters) + 1))

        for key in ("numChapters", "num_chapters", "chapter_count"):
            value = raw.get(key) or raw.get("raw", {}).get(key)
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            return list(range(1, count + 1))

        return []

    def _emit(self, event_type: str, payload: dict):
        if self.notifier:
            self.notifier(event_type, payload)
    
    def temp_dir(self):
        self.temp_dir_path = "temp"
