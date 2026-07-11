from novelcast.parser import PatreonParser


def test_parse_patreon_story():
    parser = PatreonParser()

    data = {
        "title": "Test Story",
        "author": "Oliver",
        "raw": {
            "chapters": [
                {
                    "number": 1,
                    "title": "Chapter 1",
                    "content": "Hello",
                },
                {
                    "number": 2,
                    "title": "Chapter 2",
                    "content": "World",
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
    assert story["chapters"][0]["content"] == "Hello"


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
