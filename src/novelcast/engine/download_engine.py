from pathlib import Path
from urllib.request import urlopen
import logging

logger = logging.getLogger(__name__)


class DownloadEngine:

    def __init__(self, stories_repo, chapters_repo, sync_repo, detector, adapters, file_utils):
        self.stories = stories_repo
        self.chapters = chapters_repo
        self.sync = sync_repo
        self.detector = detector
        self.adapters = adapters
        self.files = file_utils

    # -------------------------------------------------
    # ADAPTER RESOLUTION
    # -------------------------------------------------
    def get_adapter(self, url: str):
        site = self.detector.detect(url)

        if site not in self.adapters:
            raise ValueError(f"No adapter registered for site: {site}")

        return self.adapters[site]

    # -------------------------------------------------
    # MAIN SYNC ENTRYPOINT
    # -------------------------------------------------
    def download_story(self, url: str):
        """
        Used by StoryDownloadService.add_story()
        """

        adapter = self.get_adapter(url)

        logger.info(f"Syncing story: {url}")

        html = urlopen(url).read().decode("utf-8", errors="ignore")
        meta = adapter.get_metadata(html)

        # 1. create or fetch story
        story = self.stories.get_by_url(url)

        if not story:
            story_id = self.stories.create(
                meta["title"],
                meta.get("author"),
                url
            )
        else:
            story_id = story["id"]

        # 2. fetch chapter list from site
        chapters = adapter.get_chapter_list(url)

        # 3. upsert chapter index (NO DOWNLOAD YET)
        for num, title, chap_url in chapters:
            self.chapters.upsert(story_id, num, title, chap_url)

        # 4. detect missing chapters (important logic layer)
        missing = self.sync.get_missing_chapters(story_id)

        logger.info(f"Missing chapters: {len(missing)}")

        # 5. download only missing
        for num in missing:
            self.download_chapter(story_id, num, adapter)

        # 6. update sync state
        downloaded_numbers = self.chapters.get_downloaded_numbers(story_id)
        online_numbers = self.chapters.get_all_numbers(story_id)

        latest_downloaded, latest_online = self.sync.get_latest_numbers(story_id)

        self.stories.update_sync_state(
            story_id,
            downloaded=len(downloaded_numbers),
            online=len(online_numbers),
            latest_downloaded=latest_downloaded,
            latest_online=latest_online,
        )

        logger.info(f"Sync complete for story {story_id}")

        return story_id

    # -------------------------------------------------
    # CHAPTER DOWNLOAD
    # -------------------------------------------------
    def download_chapter(self, story_id: int, chapter_number: int, adapter):

        chapter = self.chapters.get_by_number(story_id, chapter_number)
        if not chapter:
            logger.warning(f"Missing chapter entry {chapter_number}")
            return

        url = chapter["url"]
        title = chapter["title"]

        html = urlopen(url).read().decode("utf-8", errors="ignore")
        content = adapter.get_chapter_content(html)

        story = self.stories.get_by_id(story_id)

        if not story:
            logger.error(f"Story not found: {story_id}")
            return

        folder = Path(story["local_path"])
        folder.mkdir(parents=True, exist_ok=True)

        filename = self.files.safe(f"c{chapter_number:04d}-{title}.html")
        path = folder / filename

        # DO NOT overwrite existing
        if path.exists():
            return

        out = f"""
        <html>
        <head><meta charset="utf-8"><title>{title}</title></head>
        <body>{content}</body>
        </html>
        """

        path.write_text(out, encoding="utf-8")

        self.chapters.mark_downloaded(
            story_id,
            chapter_number,
            str(path)
        )