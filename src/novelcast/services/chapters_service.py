from pathlib import Path
from novelcast.parser.epub_parser import DEFAULT_PATTERNS, _is_chapter, _compile


class ChaptersService:
    def __init__(self, repo):
        self.repo = repo

    def list_by_story(self, story_id: int):
        return self.repo.get_downloaded(story_id)

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
    
    def list_by_story_filtered(self,story_id: int,extra_patterns: list[str] | None = None,) -> list[dict]:    
        chapters = self.list_by_story(story_id)
        compiled = _compile(DEFAULT_PATTERNS + (extra_patterns or []))
        return [ch for ch in chapters if _is_chapter(ch.get("title", ""), compiled)]
    