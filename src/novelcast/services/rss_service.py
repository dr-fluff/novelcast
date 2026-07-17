import logging
import re
import threading
import time

from novelcast.core import setting_keys
from novelcast.db.repositories.rss_entry_repository import RssEntryRepository
from novelcast.rss import RoyalRoadRss
from novelcast.services.chapter_filter_service import ChapterFilterService
from novelcast.services.settings_service import SettingsService
from novelcast.services.story_download_service import StoryDownloadService
from novelcast.services.story_service import StoryService

logger = logging.getLogger(__name__)

class RssService:
    def __init__(
        self,
        settings: SettingsService,
        story_service: StoryService,
        download_service: StoryDownloadService,
        rss_repo: RssEntryRepository,
        chapter_filter: ChapterFilterService | None = None,
    ):
        self.settings = settings
        self.story_service = story_service
        self.download_service = download_service
        self.rss_repo = rss_repo
        self.chapter_filter = chapter_filter

        self.readers = []

        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self._running:
            return

        if self._thread and self._thread.is_alive():
            logger.error(
                "RSS start() refused: previous thread is still shutting down"
            )
            return

        if not self.settings.get(setting_keys.RSS_SETTINGS.ENABLED, default=False).value:
            logger.info("RSS service disabled")
            return

        self.readers = self.create_readers()

        if not self.readers:
            logger.info("No RSS readers enabled")
            return

        self._stop_event.clear()
        self._running = True

        self._thread = threading.Thread(
            target=self.run,
            daemon=True,
            name="rss-service",
        )

        self._thread.start()

        logger.info(
            "RSS service started readers=%s",
            [r.__class__.__name__ for r in self.readers],
        )

    def stop(self):
        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("RSS thread did not stop within timeout")
                return

        self._thread = None
        self._stop_event.clear()

    def run(self):
        while self._running:
            if not self.settings.get(setting_keys.RSS_SETTINGS.ENABLED, default=False).value:
                logger.info("RSS disabled, stopping polling loop")
                break

            self.readers = self.create_readers()

            if not self.readers:
                logger.info("No RSS readers enabled, stopping polling loop")
                break

            try:
                self.check_feeds()
            except Exception:
                logger.exception("RSS polling failed")

            interval = int(self.settings.get(setting_keys.RSS_SETTINGS.INTERVAL, default=10).value)

            if self._stop_event.wait(timeout=interval * 60):
                break

        self._running = False
        self._thread = None

    def create_readers(self):

        readers = []

        if self.settings.get(setting_keys.RSS_SETTINGS.ROYALROAD, default=False).value:
            readers.append(RoyalRoadRss(self.story_service))

        logger.info(
            "Created RSS readers=%s",
            [r.__class__.__name__ for r in readers],
        )

        return readers

    FEED_FETCH_DELAY_SECONDS = 2

    def check_feeds(self):

        for reader in self.readers:
            # ← CHANGED: bail out between readers if stop() was called
            if self._stop_event.is_set():
                return

            try:
                feed_urls = reader.get_feed_urls()

            except Exception:
                logger.exception(
                    "RSS reader failed to build feed urls: %s",
                    reader.__class__.__name__,
                )
                continue

            if not feed_urls:
                continue

            for index, (story_site_id, url) in enumerate(feed_urls):
                if self._stop_event.is_set():
                    return

                if index > 0:
                    if self._stop_event.wait(timeout=self.FEED_FETCH_DELAY_SECONDS):
                        return

                try:
                    xml = reader.fetch(url)

                    if not xml:
                        continue

                    entries = reader.parse(xml, story_site_id)

                    logger.debug(
                        "%s returned %s entries for story_site_id=%s",
                        reader.__class__.__name__,
                        len(entries),
                        story_site_id,
                    )

                    self.process_entries(entries)

                except Exception:
                    logger.exception(
                        "RSS reader failed: %s story_site_id=%s",
                        reader.__class__.__name__,
                        story_site_id,
                    )

    def process_entries(self, entries):
        entries_by_story = {}
        story_by_key = {}

        for entry in entries:
            guid = entry.get("guid")

            if not guid:
                logger.warning(
                    "RSS entry missing guid: %s",
                    entry,
                )
                continue

            if self.rss_repo.exists(
                source=entry["source"],
                guid=guid,
            ):
                logger.debug(
                    "RSS entry already processed: %s",
                    guid,
                )
                continue

            logger.info(
                "New RSS entry: %s",
                entry.get("title"),
            )

            rss_entry = self.rss_repo.create(entry)

            if not self._is_chapter_entry(entry):
                logger.info(
                    "Skipping non-chapter RSS entry: %s",
                    entry.get("title"),
                )
                self.rss_repo.mark_processed(rss_entry["id"])
                continue

            story = self.story_service.get_story_by_site_id(
                entry["source"],
                entry.get("story_site_id"),
            )

            if not story:
                logger.warning(
                    "No matching story found for RSS entry: %s",
                    entry,
                )
                continue

            story_key = story["id"]
            story_by_key[story_key] = story
            entries_by_story.setdefault(story_key, []).append((rss_entry["id"], entry))

        for story_key, id_entry_pairs in entries_by_story.items():
            story = story_by_key[story_key]
            entry_ids = [entry_id for entry_id, _ in id_entry_pairs]

            if self._already_synced_locally(story, id_entry_pairs):
                logger.info(
                    "Story already up to date locally, skipping download: story=%s",
                    story["title"],
                )
                for entry_id in entry_ids:
                    self.rss_repo.mark_processed(entry_id)
                continue

            try:
                result = self.download_service.update_story(story)

                logger.info(
                    "RSS update finished story=%s new_chapters=%s",
                    story["title"],
                    result.get("new_chapters"),
                )

                for entry_id in entry_ids:
                    self.rss_repo.mark_processed(entry_id)

            except Exception:
                logger.exception(
                    "RSS update failed for story=%s",
                    story["title"],
                )

    def _already_synced_locally(self, story, id_entry_pairs) -> bool:
        last_updated = story.get("last_updated")

        if not last_updated:
            return False

        published_dates = [entry.get("published") for _, entry in id_entry_pairs if entry.get("published")]

        if not published_dates:
            return False

        newest_entry_published = max(published_dates)

        try:
            return newest_entry_published <= last_updated
        except TypeError:
            logger.warning(
                "Could not compare RSS entry date to story.last_updated for story=%s",
                story.get("title"),
            )
            return False

    def handle_new_entry(self, entry):

        story_id = entry.get("story_site_id")

        if not story_id:
            return

        story = self.story_service.get_story_by_site_id(
            entry["source"],
            story_id,
        )

        if not story:
            logger.debug(
                "RSS entry does not match library: %s",
                story_id,
            )

            return

        logger.info(
            "RSS update for story: %s",
            story["title"],
        )

    def _is_chapter_entry(self, entry) -> bool:
        if not self.chapter_filter:
            return True

        patterns = self.chapter_filter.get_enabled_regexes()

        if not patterns:
            return True

        title = entry.get("title") or ""

        return any(re.search(pattern, title, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _is_enabled(value):
        return str(value).lower() in (
            "1",
            "true",
            "yes",
        )