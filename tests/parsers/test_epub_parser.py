from pathlib import Path

from novelcast.parser import EpubParser


def test_parse_chapter_number():
    parser = EpubParser(patterns=[r"chapter\s+(\d+)"])

    assert parser._parse_chapter_number("Chapter 12") == 12
    assert parser._parse_chapter_number("chapter 5") == 5
    assert parser._parse_chapter_number("Announcement") is None


def test_set_patterns():
    parser = EpubParser()

    parser.set_patterns([r"chapter\s+(\d+)"])

    assert parser._parse_chapter_number("Chapter 99") == 99


def test_missing_epub_raises():
    parser = EpubParser(patterns=[r"chapter\s+(\d+)"])

    missing_file = Path("/tmp/does-not-exist.epub")

    try:
        parser.extract(missing_file)
        raise AssertionError("Expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_parse_chapter_html():
    parser = EpubParser()

    html = b"""
    <html>
        <body>
            <h1>Chapter 1</h1>
            <p>Hello World</p>
        </body>
    </html>
    """

    title, content = parser._parse_chapter(html)

    assert title == "Chapter 1"
    assert "Hello World" in content


def test_parse_real_epub(sample_epub):
    parser = EpubParser(patterns=[r"chapter\s+(\d+)"])

    story = parser.parse(
        {
            "file_path": str(sample_epub),
            "title": "Test Book",
        }
    )

    assert story["title"] == "Test Book"
    assert len(story["chapters"]) > 0
