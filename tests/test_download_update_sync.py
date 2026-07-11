import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from novelcast.app.lifespan import _run_auto_check
from novelcast.services.story_download_service import StoryDownloadService
from novelcast.services.story_service import StoryService
from novelcast.services.sync_service import LibrarySyncService


class FakePipeline:
    def __init__(self):
        self.persist_calls = []
        self.append_calls = []
        self.chapters_repo = MagicMock()

    def persist(self, story_id, parsed):
        self.persist_calls.append((story_id, parsed))

    def append_new_chapters(self, story_id, parsed):
        self.append_calls.append((story_id, parsed))
        return [ch["number"] for ch in parsed.get("chapters", [])]


class TestStoryDownloadService(unittest.TestCase):
    def setUp(self):
        self.orchestrator = MagicMock()
        self.parser = MagicMock()
        self.stories_repo = MagicMock()
        self.pipeline = FakePipeline()
        self.notifier = MagicMock()
        self.service = StoryDownloadService(
            orchestrator=self.orchestrator,
            pipeline=self.pipeline,
            parser=self.parser,
            stories_repo=self.stories_repo,
            notifier=self.notifier,
        )

    def test_add_story_skips_existing_story(self):
        self.stories_repo.get_by_url.return_value = {
            "id": 123,
            "title": "Existing Story",
        }

        story_id = self.service.add_story("https://example.com/story")

        self.assertEqual(story_id, 123)
        self.orchestrator.download.assert_not_called()
        self.notifier.assert_any_call(
            "download_finished",
            {
                "download_id": unittest.mock.ANY,
                "story_id": 123,
                "title": "Existing Story",
            },
        )

    def test_add_story_persists_downloaded_story(self):
        raw = {
            "url": "https://example.com/story",
            "title": "New Story",
            "author": "Jane Doe",
            "file_path": "/tmp/story.epub",
        }
        parsed = {
            "title": "New Story",
            "author": "Jane Doe",
            "chapters": [{"number": 1}, {"number": 2}],
        }

        self.stories_repo.get_by_url.return_value = None
        self.orchestrator.download.return_value = raw
        self.parser.parse.return_value = parsed
        self.stories_repo.create.return_value = 42
        self.stories_repo.get_by_id.return_value = {"id": 42, "local_path": None}
        self.stories_repo.update_full_metadata.return_value = {"id": 42}

        story_id = self.service.add_story("https://example.com/story")

        self.assertEqual(story_id, 42)
        self.parser.parse.assert_called_once_with(raw)
        self.assertEqual(len(self.pipeline.persist_calls), 1)
        self.assertEqual(self.pipeline.persist_calls[0][0], 42)
        self.assertTrue(self.notifier.called)

    def test_update_story_returns_new_chapters(self):
        story = {"id": 101, "source_url": "https://example.com/story", "title": "Story"}
        raw = {
            "url": "https://example.com/story",
            "title": "Story",
            "author": "Jane Doe",
            "file_path": "/tmp/story.epub",
        }
        parsed = {
            "title": "Story",
            "chapters": [{"number": 1}, {"number": 2}],
        }

        self.orchestrator.download.return_value = raw
        self.parser.parse.return_value = parsed
        self.stories_repo.get_by_id.return_value = {"id": 101, "local_path": None}
        self.stories_repo.update_full_metadata.return_value = {"id": 101}
        self.pipeline.chapters_repo.get_chapter_numbers.return_value = [1]

        result = self.service.update_story(story)

        self.assertEqual(result["story_id"], 101)
        self.assertEqual(result["new_chapters"], 1)
        self.assertEqual(result["chapter_numbers"], [2])
        self.assertEqual(len(self.pipeline.persist_calls), 1)

    def test_check_story_updates_returns_pending_chapters(self):
        story = {"id": 200, "source_url": "https://example.com/story"}
        raw = {"zchapters": [1, 2, 3]}

        self.orchestrator.check_updates.return_value = raw
        self.pipeline.chapters_repo.get_chapter_numbers.return_value = [1, 2]

        result = self.service.check_story_updates(story)

        self.assertEqual(result["pending_chapters"], 1)
        self.assertEqual(result["chapter_numbers"], [3])


class TestStoryService(unittest.TestCase):
    def test_update_story_metadata_persists_auto_update_setting(self):
        repo = MagicMock()
        repo.update_full_metadata.return_value = {"id": 10}

        story_service = StoryService(repo, author_repo=None)
        updated = story_service.update_story_metadata(
            story_id=10,
            title="Title",
            author="Author",
            subtitle=None,
            description=None,
            publish_year=None,
            language=None,
            series=None,
            genres=None,
            tags=None,
            source_url=None,
            auto_update=True,
        )

        self.assertEqual(updated, {"id": 10})
        repo.set_story_setting.assert_called_once_with(
            10,
            "auto_update",
            "1",
            category="story",
            type="bool",
        )


class TestLibrarySyncService(unittest.TestCase):
    def setUp(self):
        self.stories = MagicMock()
        self.download = MagicMock()
        self.settings = MagicMock()
        self.notifier = MagicMock()
        self.sync_service = LibrarySyncService(
            stories=self.stories,
            download=self.download,
            settings=self.settings,
            notifier=self.notifier,
        )

    def test_update_all_limits_to_selected_stories(self):
        self.stories.get_all_stories.return_value = [
            {"id": 1, "source_url": "https://example.com/1"},
            {"id": 2, "source_url": "https://example.com/2"},
        ]
        self.download.update_story.side_effect = [
            {"story_id": 1, "new_chapters": 2},
        ]

        result = self.sync_service.update_all([1])

        self.assertEqual(result["stories_checked"], 1)
        self.assertEqual(result["stories_updated"], 1)
        self.assertEqual(result["new_chapters"], 2)
        self.download.update_story.assert_called_once()

    def test_check_updates_only_pending_stories(self):
        self.stories.get_all_stories.return_value = [
            {"id": 1, "source_url": "https://example.com/1"},
            {"id": 2, "source_url": "https://example.com/2"},
        ]
        self.download.check_story_updates.side_effect = [
            {"story_id": 1, "pending_chapters": 0},
            {"story_id": 2, "pending_chapters": 3},
        ]

        result = self.sync_service.check_updates()

        self.assertEqual(result["stories_checked"], 2)
        self.assertEqual(result["stories_with_updates"], 1)
        self.assertEqual(result["pending_chapters"], 3)
        self.assertEqual(result["stories"][0]["story_id"], 2)


class TestAutoSyncWorker(unittest.IsolatedAsyncioTestCase):
    async def test_run_auto_check_updates_auto_stories_when_pending(self):
        ctx = MagicMock()
        ctx.library_sync = MagicMock()
        ctx.library_sync.auto_sync_enabled.return_value = True
        ctx.library_sync.stories.get_all_stories.return_value = [
            {"id": 1, "auto_update": True, "source_url": "https://example.com/1"},
            {"id": 2, "auto_update": False, "source_url": "https://example.com/2"},
        ]
        ctx.library_sync.check_updates.return_value = {"pending_chapters": 1}
        ctx.library_sync.update_all = MagicMock()

        await _run_auto_check(ctx)

        ctx.library_sync.check_updates.assert_called_once_with([1])
        ctx.library_sync.update_all.assert_called_once_with([1])
