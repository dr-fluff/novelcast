# novelcast/pipeline/story_pipeline.py

from pathlib import Path
import copy
import json
import logging

from novelcast.utils.html import clean_html_description

logger = logging.getLogger(__name__)


class StoryPipeline:
    """
    Pure persistence layer.

    Responsibility:
    - write chapters to disk
    - store metadata in DB
    - update stats

    NO:
    - fetching
    - parsing
    - downloading
    - business logic
    """

    def __init__(self, stories_repo, chapters_repo, file_utils):
        self.stories_repo = stories_repo
        self.chapters_repo = chapters_repo
        self.file_utils = file_utils

    # ─────────────────────────────
    # STORY CONTENT PERSISTENCE
    # ─────────────────────────────
    def persist(self, story_id: int, story: dict) -> None:
        """
        story_id must already exist. The service layer owns story creation.
        story must already be fully parsed.
        """

        base_dir = self.file_utils.story_dir(
            story.get("author"),
            story.get("title"),
        )

        cover_path = self._write_cover(base_dir, story.get("cover_image"))

        epub_source_path = story.get("source_file_path")
        if epub_source_path:
            self._move_epub(epub_source_path, base_dir)

        self.stories_repo.update_paths(
            story_id,
            str(base_dir),
            str(cover_path) if cover_path else None,
        )

        chapter_numbers = []

        for ch in story.get("chapters", []):
            chapter_numbers.append(
                self._persist_chapter(story_id, base_dir, story, ch)
            )

        self._write_metadata_json(base_dir, story)
        self._update_stats(story_id, chapter_numbers)
        # update computed directory size after persisting files
        try:
            size_bytes = self.file_utils.dir_size(base_dir)
            # store as story setting to avoid schema changes
            self.stories_repo.set_story_setting(story_id, "computed.size", str(int(size_bytes)))
        except Exception:
            logger.exception("Failed to update story size setting")

    
    def get_story_by_url(self, url: str):
        return self.stories_repo.get_by_url(url)
    
    # ─────────────────────────────
    # APPEND CHAPTERS ONLY
    # ─────────────────────────────
    def append_new_chapters(self, story_id: int, story: dict):
        existing_story = self.stories_repo.get_by_id(story_id) or {}
        local_path = existing_story.get("local_path")
        base_dir = Path(local_path) if local_path else self.file_utils.story_dir(
            story.get("author"),
            story.get("title"),
        )

        # move EPUB file to story directory if present
        epub_source_path = story.get("source_file_path")
        if epub_source_path:
            self._move_epub(epub_source_path, base_dir)

        existing = self.chapters_repo.get_chapter_numbers(story_id)
        restored_chapters = self._restore_missing_chapter_files(story_id, base_dir, story)
        new_chapters = []
        online_numbers = []

        for ch in story.get("chapters", []):
            online_numbers.append(ch["number"])

            if ch["number"] in existing:
                continue

            self._persist_chapter(story_id, base_dir, story, ch)
            new_chapters.append(ch["number"])

        self._write_metadata_json(base_dir, story)
        self._update_append_stats(story_id, online_numbers)

        # update computed directory size after appending new chapters or restoring lost files
        try:
            size_bytes = self.file_utils.dir_size(base_dir)
            self.stories_repo.set_story_setting(story_id, "computed.size", str(int(size_bytes)))
        except Exception:
            logger.exception("Failed to update story size setting")

        return sorted(set(new_chapters + restored_chapters))

    # ─────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────
    def _persist_chapter(self, story_id, base_dir: Path, story: dict, ch: dict) -> int:
        title_safe = self.file_utils.safe(ch.get("title") or "")
        filename = f"{ch['number']:03d}_{title_safe or f'chapter_{ch['number']:03d}'}.html"

        path = self.file_utils.write_chapter(
            base_dir,
            filename,
            ch["content"],
        )

        story_url = story.get("source_url") or story.get("url") or ""
        chapter_url = (
            f"{story_url}#chapter-{ch['number']}"
            if story_url
            else f"file://{path}"
        )

        self.chapters_repo.upsert(
            story_id,
            ch["number"],
            ch.get("title"),
            chapter_url,
            str(path),
            1,
        )

        return ch["number"]

    def _restore_missing_chapter_files(self, story_id: int, base_dir: Path, story: dict) -> list[int]:
        chapters = self.chapters_repo.get_by_story(story_id)
        if not chapters:
            return []

        chapter_map = {ch["chapter_number"]: ch for ch in chapters}
        restored = []

        for ch in story.get("chapters", []):
            existing = chapter_map.get(ch["number"])
            if not existing:
                continue

            file_path = existing.get("file_path")
            if file_path and Path(file_path).exists():
                continue

            # Re-create missing local HTML from available parsed chapter content.
            self._persist_chapter(story_id, base_dir, story, ch)
            restored.append(ch["number"])

        return restored

    def _write_metadata_json(self, base_dir: Path, story: dict) -> None:
        metadata = story.get("raw_metadata")
        if not metadata:
            return

        metadata_copy = copy.deepcopy(metadata)
        if isinstance(metadata_copy.get("description"), str):
            metadata_copy["description"] = clean_html_description(metadata_copy["description"])

        metadata_path = base_dir / "metadata.json"
        try:
            metadata_path.write_text(
                json.dumps(metadata_copy, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to write metadata.json")

    def _update_stats(self, story_id: int, chapter_numbers: list[int]):
        total = len(chapter_numbers)
        latest = max(chapter_numbers) if chapter_numbers else None

        self.stories_repo.update_chapter_stats(
            story_id,
            total,
            total,
            latest,
            total,
            total,
        )

    def _update_append_stats(self, story_id: int, online_numbers: list[int]):
        downloaded = self.chapters_repo.get_downloaded_numbers(story_id)
        total_local = len(self.chapters_repo.get_chapter_numbers(story_id))

        self.stories_repo.update_chapter_stats(
            story_id,
            max(total_local, len(online_numbers)),
            len(downloaded),
            max(downloaded) if downloaded else None,
            max(online_numbers) if online_numbers else None,
            len(online_numbers),
        )

    def _move_epub(self, source_path: str, base_dir: Path):
        source = Path(source_path)
        if not source.exists():
            return

        dest = base_dir / self.file_utils.safe(source.name)
        source.replace(dest)

    def _write_cover(self, base_dir: Path, cover_bytes: bytes | None):
        if not cover_bytes:
            return None

        cover_path = base_dir / "cover.jpg"

        try:
            with open(cover_path, "wb") as f:
                f.write(cover_bytes)
            return str(cover_path)
        except Exception as e:
            logger.warning("Failed to write cover: %s", e)
            return None
