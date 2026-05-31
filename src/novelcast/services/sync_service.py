# novelcast/services/sync_service.py

import logging
from datetime import datetime, time, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class LibrarySyncService:
    def __init__(self, stories, download, settings, notifier=None):
        self.stories = stories
        self.download = download
        self.settings = settings
        self.notifier = notifier
        self._lock = Lock()
        self._last_update_check = {
            "status": "not_checked",
            "stories_checked": 0,
            "stories_with_updates": 0,
            "pending_chapters": 0,
            "stories": [],
        }

    def auto_sync_enabled(self) -> bool:
        return self._library_setting("auto_update", True) in (True, 1, "1", "true", "True")

    def update_on_startup_enabled(self) -> bool:
        return self._library_setting("update_on_startup", True) in (True, 1, "1", "true", "True")

    def interval_seconds(self) -> int:
        try:
            hours = int(self._library_setting("update_interval_hours", 24))
        except (TypeError, ValueError):
            hours = 24

        return max(1, hours) * 60 * 60

    def next_check_delay_seconds(self) -> int:
        try:
            interval_hours = max(1, int(self._library_setting("update_interval_hours", 24)))
        except (TypeError, ValueError):
            interval_hours = 24

        update_time_value = self._parse_update_time(self._library_setting("update_time", "02:00"))
        now = datetime.now()
        next_run = datetime.combine(now.date(), update_time_value)

        while next_run <= now:
            next_run += timedelta(hours=interval_hours)

        return max(0, int((next_run - now).total_seconds()))

    def _parse_update_time(self, value: str) -> time:
        if not isinstance(value, str):
            return time(2, 0)

        try:
            hour_str, minute_str = value.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            return time(hour % 24, minute % 60)
        except Exception:
            return time(2, 0)

    def run_once(self) -> dict:
        if not self._lock.acquire(blocking=False):
            return {"status": "already_running", "stories_checked": 0, "stories_updated": 0, "new_chapters": 0}

        try:
            stories = self.stories.get_all_stories()
            checked = 0
            updated = 0
            new_chapters = 0

            self._emit("sync_started", {"stories": len(stories)})

            for story in stories:
                if not story.get("source_url"):
                    continue

                checked += 1
                try:
                    result = self.download.sync_story(story)
                except Exception:
                    logger.exception("Failed to sync story %s", story.get("id"))
                    continue

                count = int(result.get("new_chapters", 0) or 0)
                if count:
                    updated += 1
                    new_chapters += count

            payload = {
                "status": "finished",
                "stories_checked": checked,
                "stories_updated": updated,
                "new_chapters": new_chapters,
            }
            self._emit("sync_finished", payload)
            return payload
        finally:
            self._lock.release()

    def check_updates(self) -> dict:
        if not self._lock.acquire(blocking=False):
            return {**self._last_update_check, "status": "already_running"}

        try:
            stories = self.stories.get_all_stories()
            checked = 0
            pending_chapters = 0
            pending_stories = []

            self._emit("sync_check_started", {"stories": len(stories)})

            for story in stories:
                if not story.get("source_url"):
                    continue

                checked += 1
                try:
                    result = self.download.check_story_updates(story)
                except Exception:
                    logger.exception("Failed to check story %s", story.get("id"))
                    continue

                count = int(result.get("pending_chapters", 0) or 0)
                if not count:
                    continue

                pending_chapters += count
                pending_stories.append(result)

            self._last_update_check = {
                "status": "finished",
                "stories_checked": checked,
                "stories_with_updates": len(pending_stories),
                "pending_chapters": pending_chapters,
                "stories": pending_stories,
            }

            self._emit("sync_check_finished", self._last_update_check)
            return self._last_update_check
        finally:
            self._lock.release()

    def pending_count(self) -> int:
        return int(self._last_update_check.get("stories_with_updates", 0) or 0)

    def pending_chapter_count(self) -> int:
        return int(self._last_update_check.get("pending_chapters", 0) or 0)

    def last_update_check(self) -> dict:
        return dict(self._last_update_check)

    def _library_setting(self, key: str, default=None):
        return self.settings.get_resolved_server_settings().get("library", {}).get(key, default)

    def _emit(self, event_type: str, payload: dict):
        if self.notifier:
            self.notifier(event_type, payload)
