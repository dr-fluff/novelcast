# novelcast/services/story_download_service.py
import logging
import uuid

logger = logging.getLogger(__name__)


class StoryDownloadService:
    def __init__(self, selector, parser, pipeline, ws_manager=None):
        self.selector = selector
        self.parser = parser
        self.pipeline = pipeline
        self.ws_manager = ws_manager

    # ----------------------------
    # WebSocket helper
    # ----------------------------
    async def notify(self, payload: dict):
        if self.ws_manager:
            await self.ws_manager.send(payload)

    # ----------------------------
    # Add story (no changes needed)
    # ----------------------------
    def add_story(self, url: str):
        logger.info("Starting story download", extra={"url": url})
        download_id = str(uuid.uuid4())
        self._notify_download_start(url, download_id)

        try:
            engine = self.selector.get_engine(url)

            raw = engine.fetch(url)
            parsed = self.parser.parse(raw)

            parsed["source_url"] = raw.get("url")
            parsed["source_file_path"] = raw.get("file_path")

            story_id = self.pipeline.persist(parsed)
            print(raw)
            self._notify_story_added(story_id, parsed, download_id)
            self._notify_download_finished(download_id, story_id, parsed)
            return story_id

        except Exception as e:
            logger.error("Error during story download", exc_info=e)
            self._notify_download_failed(download_id, url, str(e))
            raise RuntimeError(str(e)) from e

    # ----------------------------
    # SYNC WITH REAL-TIME EVENTS
    # ----------------------------
    def sync_story(self, story: dict):
        url = story["source_url"]

        logger.info("Syncing story", extra={"url": url})

        engine = self.selector.get_engine(url)
        raw = engine.fetch(url)
        parsed = self.parser.parse(raw)

        latest_online = parsed.get("total_chapters", 0)
        current_downloaded = story.get("downloaded_chapters", 0)

        # notify start
        self._notify_sync_start(story)

        if latest_online <= current_downloaded:
            self._notify_no_updates(story)
            return {"status": "up-to-date"}

        new_chapters = engine.fetch_chapters(
            url,
            start=current_downloaded + 1
        )

        self._notify_progress(story, len(new_chapters))

        self.pipeline.append_chapters(story["id"], new_chapters)

        self.pipeline.update_stats(
            story["id"],
            total=latest_online,
            downloaded=current_downloaded + len(new_chapters)
        )

        self._notify_finished(story, len(new_chapters))

        return {"status": "updated", "new_chapters": len(new_chapters)}

    # ----------------------------
    # Notification helpers
    # ----------------------------
    def _notify_sync_start(self, story):
        self._send({
            "type": "sync_started",
            "story_id": story["id"],
            "title": story.get("title")
        })

    def _notify_no_updates(self, story):
        self._send({
            "type": "sync_no_changes",
            "story_id": story["id"]
        })

    def _notify_progress(self, story, count):
        self._send({
            "type": "sync_progress",
            "story_id": story["id"],
            "new_chapters": count
        })

    def _notify_finished(self, story, count):
        self._send({
            "type": "sync_finished",
            "story_id": story["id"],
            "new_chapters": count
        })

    def _notify_download_start(self, source_url, download_id):
        self._send({
            "type": "download_started",
            "download_id": download_id,
            "source_url": source_url,
        })

    def _notify_story_added(self, story_id, story, download_id=None):
        payload = {
            "type": "story_added",
            "story_id": story_id,
            "title": story.get("title"),
            "source_url": story.get("source_url"),
        }
        if download_id:
            payload["download_id"] = download_id
        self._send(payload)

    def _notify_download_finished(self, download_id, story_id, story):
        self._send({
            "type": "download_finished",
            "download_id": download_id,
            "story_id": story_id,
            "title": story.get("title"),
        })

    def _notify_download_failed(self, download_id, source_url, error):
        self._send({
            "type": "download_failed",
            "download_id": download_id,
            "source_url": source_url,
            "error": error,
        })

    def _send(self, payload):
        # sync wrapper (safe from thread usage)
        try:
            manager = self.ws_manager
            if manager:
                import anyio
                anyio.from_thread.run(manager.send, payload)
        except Exception as e:
            logger.warning(f"WS notify failed: {e}")