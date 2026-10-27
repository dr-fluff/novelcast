from novelcast.parser import PatreonParser


def test_parse_patreon_story():
    parser = PatreonParser()

    data = {
        "title": "Test Story",
        "author": "Oliver",
        "raw": {
            "post_records": [
                {
                    "title": "Chapter 1",
                    "raw_content": "Hello",
                    "content_format": "html",
                },
                {
                    "title": "Chapter 2",
                    "raw_content": "World",
                    "content_format": "html",
                },
            ]
        },
    }

    story = parser.parse(data)

    assert story["title"] == "Test Story"
    assert story["author"] == "Oliver"

    assert len(story["chapters"]) == 2

    assert story["chapters"][0]["number"] == 1
    assert story["chapters"][0]["title"] == "Chapter 1"
    assert story["chapters"][0]["content"] == "<p>Hello</p>"


def test_parse_empty_chapters():
    parser = PatreonParser()

    story = parser.parse(
        {
            "title": "Empty",
            "raw": {},
        }
    )

    assert story["chapters"] == []


def test_default_title():
    parser = PatreonParser()

    story = parser.parse({"raw": {}})

    assert story["title"] == "Unknown"
