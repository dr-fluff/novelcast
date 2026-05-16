# novelcast/pipeline/story_pipeline.py

from pathlib import Path
import logging

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

        self._update_stats(story_id, chapter_numbers)

    
    def get_story_by_url(self, url: str):
        return self.stories_repo.get_by_url(url)
    
    # ─────────────────────────────
    # APPEND CHAPTERS ONLY
    # ─────────────────────────────
    def append_new_chapters(self, story_id: int, story: dict):
        base_dir = self.file_utils.story_dir(
            story.get("author"),
            story.get("title"),
        )

        existing = self.chapters_repo.get_chapter_numbers(story_id)
        new_chapters = []

        for ch in story.get("chapters", []):
            if ch["number"] in existing:
                continue

            self._persist_chapter(story_id, base_dir, story, ch)
            new_chapters.append(ch["number"])

        return new_chapters

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
