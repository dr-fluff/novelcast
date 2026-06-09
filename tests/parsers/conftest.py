# tests/parsers/conftest.py

import pytest
from pathlib import Path

def assert_valid_story(story):
    assert isinstance(story, dict)

    assert "title" in story
    assert "author" in story
    assert "chapters" in story

    assert isinstance(story["chapters"], list)

    for chapter in story["chapters"]:
        assert "number" in chapter
        assert "title" in chapter
        assert "content" in chapter


@pytest.fixture
def sample_epub():
    return Path(__file__).resolve().parents[1] / "fixtures" / "sample.epub"