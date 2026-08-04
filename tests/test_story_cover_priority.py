from pathlib import Path

from novelcast.pipeline.story_pipeline import StoryPipeline
from novelcast.services.story_service import StoryService
from novelcast.utils.files import FileUtils


class DummyStoriesRepo:
    def __init__(self, existing_cover_path=None):
        self.existing_cover_path = existing_cover_path
        self.updated_paths = []
        self.updated_covers = []

    def get_by_id(self, story_id):
        return {"id": story_id, "cover_path": self.existing_cover_path, "local_path": None}

    def get_existing_local_paths(self, exclude_story_id=None):
        return set()

    def update_paths(self, story_id, local_path, cover_path=None):
        if cover_path is not None and self.existing_cover_path is None:
            self.existing_cover_path = cover_path
        self.updated_paths.append((story_id, local_path, cover_path))

    def set_story_setting(self, story_id, name, value):
        return None

    def update_cover(self, story_id, cover_path):
        self.updated_covers.append((story_id, cover_path))

    def update_chapter_stats(self, story_id, total_chapters, downloaded_chapters, latest_online_chapter, latest_downloaded_chapter, online_chapters):
        return None


class DummyChaptersRepo:
    pass


def test_pipeline_preserves_existing_cover_when_metadata_cover_is_available(tmp_path):
    repo = DummyStoriesRepo(existing_cover_path="custom-cover.jpg")
    pipeline = StoryPipeline(repo, DummyChaptersRepo(), FileUtils(base_dir=tmp_path))

    pipeline.persist(
        7,
        {
            "author": "Alice",
            "title": "Example",
            "cover_image": b"fake",
            "chapters": [],
        },
    )

    assert repo.updated_paths[-1][2] is None


def test_story_service_updates_cover_path():
    repo = DummyStoriesRepo()
    service = StoryService(repo)

    service.update_story_cover(42, "uploaded-cover.jpg")

    assert repo.updated_covers == [(42, "uploaded-cover.jpg")]
