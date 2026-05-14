# novelcast/services/story_download_service.py

import logging
import uuid

from novelcast.utils.url_normalizer import normalize_story_url

logger = logging.getLogger(__name__)


class StoryDownloadService:
    def __init__(self, selector, parser, pipeline, notifier=None):
        self.selector = selector
        self.parser = parser
        self.pipeline = pipeline
        self.notifier = notifier  # NotifierService | None

    # ─────────────────────────────
    # Public API
    # ─────────────────────────────

    def add_story(self, url: str):
        """Download and persist a new story. Safe to call from a worker thread."""
        logger.info("Starting story download", extra={"url": url})

        normalized_url = normalize_story_url(url)

        existing = self.pipeline.stories_repo.get_by_url(normalized_url)
        if existing:
            logger.info("Story already exists", extra={"story_id": existing["id"]})
            self._send({"type": "story_exists", "story_id": existing["id"], "source_url": normalized_url})
            return existing["id"]

        download_id = str(uuid.uuid4())
        self._send({"type": "download_started", "download_id": download_id, "source_url": normalized_url})

        try:
            engine = self.selector.get_engine(normalized_url)
            raw = engine.fetch(normalized_url)
            parsed = self.parser.parse(raw)

            parsed["source_url"] = normalize_story_url(raw.get("url") or normalized_url)
            parsed["source_file_path"] = raw.get("file_path")

            story_id = self.pipeline.persist(parsed)

            self._send({
                "type": "story_added",
                "story_id": story_id,
                "title": parsed.get("title"),
                "source_url": parsed.get("source_url"),
                "download_id": download_id,
            })
            self._send({
                "type": "download_finished",
                "download_id": download_id,
                "story_id": story_id,
                "title": parsed.get("title"),
            })

            return story_id

        except Exception as e:
            logger.error("Error during story download", exc_info=e)
            self._send({
                "type": "download_failed",
                "download_id": download_id,
                "source_url": normalized_url,
                "error": str(e),
            })
            raise RuntimeError(str(e)) from e

    def sync_story(self, story: dict) -> dict:
        """Fetch new chapters for an existing story. Safe to call from a worker thread."""
        url = story["source_url"]
        logger.info("Syncing story", extra={"url": url})

        engine = self.selector.get_engine(url)
        raw = engine.fetch(url)
        parsed = self.parser.parse(raw)

        latest_online = parsed.get("total_chapters", 0)
        current_downloaded = story.get("downloaded_chapters", 0)

        self._send({"type": "sync_started", "story_id": story["id"], "title": story.get("title")})

        if latest_online <= current_downloaded:
            self._send({"type": "sync_no_changes", "story_id": story["id"]})
            return {"status": "up-to-date", "new_chapters": 0}

        new_chapters = engine.fetch_chapters(url, start=current_downloaded + 1)

        self._send({"type": "sync_progress", "story_id": story["id"], "new_chapters": len(new_chapters)})

        self.pipeline.append_chapters(story["id"], new_chapters)
        self.pipeline.update_stats(
            story["id"],
            total=latest_online,
            downloaded=current_downloaded + len(new_chapters),
        )

        self._send({"type": "sync_finished", "story_id": story["id"], "new_chapters": len(new_chapters)})

        return {"status": "updated", "new_chapters": len(new_chapters)}

    # ─────────────────────────────
    # Internal
    # ─────────────────────────────

    def _send(self, payload: dict) -> None:
        if self.notifier:
            self.notifier.broadcast(payload)