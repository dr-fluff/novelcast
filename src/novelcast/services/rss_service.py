import logging
import re
import threading
import time

from novelcast.services import SettingsService, StoryService, StoryDownloadService
from novelcast.db.repositories.rss_entry_repository import RssEntryRepository
from novelcast.services.chapter_filter_service import ChapterFilterService

from novelcast.rss import RoyalRoadRss


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


    def _get_settings(self):
        return self.settings.get_resolved_server_settings()


    def start(self):
        if self._running:
            return

        settings = self._get_settings()

        if not self._is_enabled(
            settings.get("rss", {}).get("enabled")
        ):
            logger.info("RSS service disabled")
            return


        self.readers = self.create_readers()

        if not self.readers:
            logger.info("No RSS readers enabled")
            return


        self._running = True

        self._thread = threading.Thread(
            target=self.run,
            daemon=True,
            name="rss-service",
        )

        self._thread.start()

        logger.info(
            "RSS service started readers=%s",
            [
                r.__class__.__name__
                for r in self.readers
            ],
        )


    def stop(self):
        self._running = False

        if self._thread:
            self._thread.join(timeout=5)


    def run(self):

        while self._running:

            try:
                self.check_feeds()

            except Exception:
                logger.exception(
                    "RSS polling failed"
                )


            interval = int(
                self._get_settings()
                .get("rss", {})
                .get("interval", 10)
            )

            time.sleep(interval * 60)



    def create_readers(self):

        rss = self._get_settings().get(
            "rss",
            {}
        )

        readers = []

        if self._is_enabled(
            rss.get("royalroad")
        ):
            readers.append(
                RoyalRoadRss(self.story_service)
            )


        logger.info(
            "Created RSS readers=%s",
            [
                r.__class__.__name__
                for r in readers
            ],
        )

        return readers



    # Minimum spacing between consecutive feed fetches to a single reader's
    # source (e.g. RoyalRoad), so tracking many auto-update stories doesn't
    # fire a burst of requests in the same instant and trip rate limiting.
    FEED_FETCH_DELAY_SECONDS = 2

    def check_feeds(self):

        for reader in self.readers:

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

                if index > 0:
                    time.sleep(self.FEED_FETCH_DELAY_SECONDS)

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
            entries_by_story.setdefault(story_key, []).append(
                (rss_entry["id"], entry)
            )

        # One update_story call per unique story in this batch, no matter
        # how many new RSS entries it had (e.g. a bulk chapter release
        # shouldn't trigger a full re-download per chapter).
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
                result = self.download_service.update_story(
                    story
                )

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
        """Local check to avoid a redundant download when the story's last
        successful sync already covers every entry in this batch. This
        matters most the first time a story's feed is polled after
        auto_update is turned on: every RSS item looks "new" to rss_entries
        (we've never seen its guid before), even if the story was already
        fully up to date on disk before auto_update was ever enabled."""
        last_updated = story.get("last_updated")

        if not last_updated:
            # No local sync timestamp to compare against — safer to let
            # the actual update_story call decide than to guess.
            return False

        published_dates = [
            entry.get("published")
            for _, entry in id_entry_pairs
            if entry.get("published")
        ]

        if not published_dates:
            return False

        newest_entry_published = max(published_dates)

        try:
            return newest_entry_published <= last_updated
        except TypeError:
            # Naive vs. aware datetime mismatch or similar — don't skip,
            # let update_story do the real check instead of guessing.
            logger.warning(
                "Could not compare RSS entry date to story.last_updated for story=%s",
                story.get("title"),
            )
            return False



    def handle_new_entry(self, entry):

        story_id = entry.get(
            "story_site_id"
        )

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

        # Later:
        # self.sync_service.update_story(story["id"])



    def _is_chapter_entry(self, entry) -> bool:
        """Return True if this RSS entry's title looks like an actual
        chapter release, using the same DB-stored regex patterns
        ChaptersService uses to separate real chapters from author's
        notes/announcements (e.g. "<Not a Chapter> Important Information
        for Readers...").

        Unlike ChaptersService.list_by_story_filtered, which returns an
        empty list when no patterns are enabled (fine for a UI listing),
        we default to treating every entry as a chapter when there's no
        chapter_filter or no enabled patterns — silently skipping every
        RSS entry because patterns happen to be unset would be a much
        worse failure mode here than occasionally over-triggering.
        """
        if not self.chapter_filter:
            return True

        patterns = self.chapter_filter.get_enabled_regexes()

        if not patterns:
            return True

        title = entry.get("title") or ""

        return any(
            re.search(pattern, title, re.IGNORECASE)
            for pattern in patterns
        )


    @staticmethod
    def _is_enabled(value):
        return str(value).lower() in (
            "1",
            "true",
            "yes",
        )