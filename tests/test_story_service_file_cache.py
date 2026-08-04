from pathlib import Path

from novelcast.services.story_service import StoryService


class DummyRepo:
    def get_by_id(self, story_id):
        return {"id": story_id, "local_path": str(Path(__file__).parent / "fixtures" / "story_files")}

    def get_all(self):
        return []

    def restore_local_cover_paths(self):
        return 0

    def get_by_url(self, url):
        return None

    def create(self, title, author=None, url=None):
        return 1

    def delete_with_relations(self, story_id):
        return None

    def get_chapter_file_paths(self, story_id):
        return []

    def update_full_metadata(self, *args, **kwargs):
        return None

    def set_story_setting(self, *args, **kwargs):
        return None

    def get_story_setting(self, *args, **kwargs):
        return None


def test_get_story_files_uses_cache_for_same_directory(tmp_path):
    story_dir = tmp_path / "story"
    story_dir.mkdir()
    (story_dir / "a.txt").write_text("hello", encoding="utf-8")

    service = StoryService(DummyRepo())
    story = {"id": 1, "local_path": str(story_dir)}

    service.get_story = lambda story_id: story

    first = service.get_story_files(1)
    second = service.get_story_files(1)

    assert len(first) == 1
    assert first == second
