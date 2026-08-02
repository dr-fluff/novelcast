# novelcast/services/chapters_service.py

import re
from pathlib import Path


class ChaptersService:
    def __init__(self, repo, chapter_filter=None):
        """
        Args:
            repo: ChapterRepository
            chapter_filter: ChapterFilterService (optional, for list_by_story_filtered)
        """
        self.repo = repo
        self.chapter_filter = chapter_filter

    def list_by_story(self, story_id: int):
        return self.repo.get_downloaded(story_id)

    def get_downloaded_ids(self, story_id: int) -> list[int]:
        """Lightweight variant of list_by_story() — only chapter IDs, in order.
        Use this instead of list_by_story() whenever only IDs are needed
        (e.g. computing prev/next chapter or read/unread state), since
        list_by_story()/get_downloaded() triggers an N+1 query (one extra
        query per chapter to resolve its canonical file via the lazy-loaded
        `files` relationship in _to_dict()). This method never touches
        that relationship, so it stays a single query regardless of how
        many chapters the story has."""
        return self.repo.get_downloaded_ids(story_id)

    def get_chapter(self, chapter_id: int):
        return self.repo.get_by_id(chapter_id)

    def get_chapter_ids_by_story(self, story_id: int):
        return self.repo.get_chapter_numbers(story_id)

    def read_chapter(self, chapter_id: int):
        chapter = self.get_chapter(chapter_id)
        if not chapter:
            return None

        file_path = chapter.get("file_path")
        if not file_path:
            return None

        path = Path(file_path)
        if not path.exists():
            return None

        return path.read_text(encoding="utf-8", errors="ignore")

    def list_by_story_filtered(self, story_id: int) -> list[dict]:
        """
        Return chapters that match enabled chapter detection patterns from DB.
        Requires chapter_filter service to be injected.
        """
        if not self.chapter_filter:
            # Fallback: return all chapters if no filter service
            return self.list_by_story(story_id)

        chapters = self.list_by_story(story_id)
        patterns = self.chapter_filter.get_enabled_regexes()

        if not patterns:
            return []

        # Compile patterns once
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        # Return chapters that match any pattern
        return [ch for ch in chapters if any(r.search(ch.get("title", "")) for r in compiled)]