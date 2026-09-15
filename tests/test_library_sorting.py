from datetime import UTC, datetime

from novelcast.api.routes.pages.helpers import enrich_story_progress, sort_stories


def test_latest_chapter_updated_sorts_newest_first():
    stories = [
        {"id": 1, "title": "Earlier", "latest_chapter_updated_at": datetime(2026, 1, 1, tzinfo=UTC)},
        {"id": 2, "title": "Later", "latest_chapter_updated_at": datetime(2026, 2, 1, tzinfo=UTC)},
        {"id": 3, "title": "No chapters", "latest_chapter_updated_at": None},
    ]

    result = sort_stories(stories, "latest_chapter_updated")

    assert [story["id"] for story in result] == [2, 1, 3]


def test_latest_chapter_updated_can_sort_oldest_first():
    stories = [
        {"id": 1, "title": "Earlier", "latest_chapter_updated_at": datetime(2026, 1, 1, tzinfo=UTC)},
        {"id": 2, "title": "Later", "latest_chapter_updated_at": datetime(2026, 2, 1, tzinfo=UTC)},
    ]

    result = sort_stories(stories, "latest_chapter_updated", direction="asc")

    assert [story["id"] for story in result] == [1, 2]


def test_last_read_sorts_most_recently_read_first():
    stories = enrich_story_progress(
        [
            {"id": 1, "title": "Earlier", "downloaded_chapters": 1},
            {"id": 2, "title": "Later", "downloaded_chapters": 1},
            {"id": 3, "title": "Unread", "downloaded_chapters": 0},
        ],
        [
            {"story_id": 1, "furthest_chapter_number": 1, "updated_at": datetime(2026, 1, 1, tzinfo=UTC)},
            {"story_id": 2, "furthest_chapter_number": 1, "updated_at": datetime(2026, 2, 1, tzinfo=UTC)},
        ],
    )

    result = sort_stories(stories, "last_read")

    assert [story["id"] for story in result] == [2, 1, 3]
