from novelcast.db.models.settings import StorySetting
from novelcast.db.models.story import Story
from novelcast.db.repositories.stories_repository import _to_dict


def make_story(settings=None):
    story = Story(title="Example", author="Author", source_url="https://example.com")
    story.settings = settings or []
    story.genres = []
    story.tags = []
    story.series = []
    return story


def test_hide_author_notes_defaults_to_true_when_unset():
    story = make_story()

    assert _to_dict(story)["hide_author_notes"] is True


def test_hide_author_notes_respects_explicit_false():
    story = make_story(
        [
            StorySetting(name="hide_author_notes", value="0"),
        ]
    )

    assert _to_dict(story)["hide_author_notes"] is False


def test_hide_author_notes_respects_explicit_true():
    story = make_story(
        [
            StorySetting(name="hide_author_notes", value="1"),
        ]
    )

    assert _to_dict(story)["hide_author_notes"] is True
