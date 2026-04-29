# novelcast/services/story_service.py

from pathlib import Path

class StoryService:
    def __init__(self, repo):
        self.repo = repo

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path

        candidate = Path.cwd() / path
        if candidate.exists():
            return candidate

        project_root = Path(__file__).resolve().parents[3]
        candidate = project_root / path
        if candidate.exists():
            return candidate

        return path

    def get_all_stories(self):
        return self.repo.get_all()

    def get_story(self, story_id: int):
        return self.repo.get_by_id(story_id)

    def create_story(self, title, author=None, url=None):
        return self.repo.create(title, author, url)

    def delete_story(self, story_id: int):
        story = self.get_story(story_id)
        if not story:
            return False

        local_path = story.get("local_path")
        if local_path:
            path = self._resolve_path(local_path)
            if path.is_dir():
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()

        chapter_paths = self.repo.get_chapter_file_paths(story_id)
        for file_path in chapter_paths:
            path = self._resolve_path(file_path)
            if path.exists():
                path.unlink()

        cover_path = story.get("cover_path")
        if cover_path and not cover_path.startswith(("http://", "https://", "/static/")):
            cover_file = self._resolve_path(cover_path)
            if cover_file.exists():
                cover_file.unlink()

        self.repo.delete_with_relations(story_id)
        return True

    def get_by_url(self, url: str):
        return self.repo.get_by_url(url)