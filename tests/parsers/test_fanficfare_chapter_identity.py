
from novelcast.parser.fanficfare_parser import FanFicFareParser


def test_preserves_source_chapter_url_and_source_chapter_number():
    parser = FanFicFareParser()
    chapter_url = (
        "https://www.royalroad.com/fiction/40920/"
        "the-path-of-ascension/chapter/3796761/"
        "the-path-of-ascension-chapter-509"
    )

    story = parser.parse(
        {
            "title": "The Path of Ascension",
            "author": "Example Author",
            "raw": {
                "chapters": [
                    {
                        "title": "Chapter 509",
                        "content": "<p>Chapter text</p>",
                    }
                ],
                "zchapters": [
                    [
                        1,
                        {
                            "title": "The Path of Ascension Chapter 509",
                            "url": chapter_url,
                            "date": "2026-09-28",
                        },
                    ]
                ],
            },
        }
    )

    assert len(story["chapters"]) == 1
    chapter = story["chapters"][0]
    assert chapter["url"] == chapter_url
    assert chapter["number"] == 1
    assert chapter["content"] == "<p>Chapter text</p>"


def test_does_not_guess_metadata_from_a_nearby_chapter():
    parser = FanFicFareParser()

    story = parser.parse(
        {
            "title": "Example",
            "author": "Example Author",
            "raw": {
                "chapters": [
                    {
                        "title": "Unmatched chapter title",
                        "content": "<p>Text</p>",
                    }
                ],
                "zchapters": [
                    [
                        2,
                        {
                            "title": "A completely different chapter",
                            "url": (
                                "https://www.royalroad.com/fiction/123/"
                                "chapter/456/wrong-chapter"
                            ),
                            "date": "2026-09-28",
                        },
                    ]
                ],
            },
        }
    )

    assert len(story["chapters"]) == 1
    assert story["chapters"][0]["url"] is None
