from pathlib import Path


class ChaptersService:
    def __init__(self, repo):
        self.repo = repo

    def list_by_story(self, story_id: int):
        return self.repo.list_downloaded_by_story(story_id)

    def get_chapter(self, chapter_id: int):
        return self.repo.get_by_id(chapter_id)

    def get_chapter_ids_by_story(self, story_id: int):
        return self.repo.get_ids_by_story(story_id)

    def read_chapter(self, chapter_id: int):
        chapter = self.get_chapter(chapter_id)
        if not chapter or not chapter.get("file_path"):
            return None

        path = Path(chapter["file_path"])
        if not path.exists():
            return None

        return path.read_text(encoding="utf-8", errors="ignore")