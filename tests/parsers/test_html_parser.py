from novelcast.parser import HtmlParser


def test_html_parser_returns_story():
    parser = HtmlParser()

    story = parser.parse(
        {
            "title": "HTML Story",
            "author": "Oliver",
            "file_path": "/tmp/test.html",
        }
    )

    assert story["title"] == "HTML Story"
    assert story["author"] == "Oliver"
    assert story["chapters"] == []


def test_html_parser_default_title():
    parser = HtmlParser()

    story = parser.parse({})

    assert story["title"] == "Unknown"