
from pathlib import Path

from novelcast.pipeline.story_pipeline import StoryPipeline


class FakeFileUtils:
    def safe(self, value):
        return value.replace("/", "_")

    def write_chapter(self, base_dir, filename, content):
        path = Path(base_dir) / filename
        path.write_text(content, encoding="utf-8")
        return path


class FakeChaptersRepository:
    def __init__(self):
        self.upserts = []

    def upsert(self, *args):
        self.upserts.append(args)


def test_persist_chapter_preserves_source_url(tmp_path):
    chapters_repo = FakeChaptersRepository()
    pipeline = StoryPipeline(
        stories_repo=None,
        chapters_repo=chapters_repo,
        file_utils=FakeFileUtils(),
    )

    source_url = (
        "https://www.royalroad.com/fiction/40920/"
        "the-path-of-ascension/chapter/3796761/"
        "the-path-of-ascension-chapter-509"
    )
    chapter = {
        "number": 1,
        "title": "Chapter 509",
        "url": source_url,
        "content": "<p>Test chapter</p>",
    }

    pipeline._persist_chapter(
        story_id=1,
        base_dir=tmp_path,
        story={
            "source_url": "https://www.royalroad.com/fiction/40920/the-path-of-ascension",
        },
        ch=chapter,
    )

    assert len(chapters_repo.upserts) == 1
    saved_url = chapters_repo.upserts[0][3]
    assert saved_url == source_url
    assert "#chapter-1" not in saved_url


class FakeStoriesRepository:
    def __init__(self, local_path):
        self.local_path = str(local_path)

    def get_by_id(self, story_id):
        return {"local_path": self.local_path}

    def set_story_setting(self, *args):
        pass
    
    def update_chapter_stats(self, *args):
        pass


class FakeAppendChaptersRepository(FakeChaptersRepository):
    def get_chapter_numbers(self, story_id):
        return {1}

    def get_by_story(self, story_id):
        return []
    
    def get_downloaded_numbers(self, story_id):
        return set()
    
    

def test_append_does_not_report_existing_chapter_as_new(tmp_path):
    chapters_repo = FakeAppendChaptersRepository()
    pipeline = StoryPipeline(
        stories_repo=FakeStoriesRepository(tmp_path),
        chapters_repo=chapters_repo,
        file_utils=FakeFileUtils(),
    )

    result = pipeline.append_new_chapters(
        story_id=1,
        story={
            "author": "Test Author",
            "title": "Test Story",
            "source_url": "https://example.com/story",
            "chapters": [
                {
                    "number": 1,
                    "title": "Chapter 1",
                    "url": "https://example.com/story/chapter/1",
                    "content": "<p>Existing chapter</p>",
                },
                {
                    "number": 2,
                    "title": "Chapter 2",
                    "url": "https://example.com/story/chapter/2",
                    "content": "<p>New chapter</p>",
                },
            ],
        },
    )

    assert result == [2]
    assert len(chapters_repo.upserts) == 1
    assert chapters_repo.upserts[0][1] == 2