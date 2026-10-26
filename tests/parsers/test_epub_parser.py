from pathlib import Path
from zipfile import ZipFile

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
    parser = EpubParser(patterns=[r"ch\.?\s*(\d+)"])

    story = parser.parse(
        {
            "file_path": str(sample_epub),
            "title": "Test Book",
        }
    )

    assert story["title"] == "Test Book"
    assert len(story["chapters"]) > 0


def test_extract_uses_spine_order_for_mixed_chapter_labels(tmp_path):
    """Decimal author labels must not overwrite the preceding whole chapter."""
    epub_path = tmp_path / "mixed-labels.epub"
    titles = ["1. A New Skin", "2. Lemon", "2.1 Otherworldly", "2.10 Reaper", "3. Pete's"]

    with ZipFile(epub_path, "w") as epub:
        epub.writestr(
            "META-INF/container.xml",
            '''<?xml version="1.0"?>
            <container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>''',
        )
        manifest = "".join(
            f'<item id="chapter-{index}" href="chapter-{index}.xhtml" />'
            for index in range(1, len(titles) + 1)
        )
        spine = "".join(f'<itemref idref="chapter-{index}" />' for index in range(1, len(titles) + 1))
        epub.writestr("OEBPS/content.opf", f"<package><manifest>{manifest}</manifest><spine>{spine}</spine></package>")
        for index, title in enumerate(titles, 1):
            epub.writestr(
                f"OEBPS/chapter-{index}.xhtml",
                f"<html><body><h1>{title}</h1><p>Chapter content {index}</p></body></html>",
            )

    parser = EpubParser(patterns=[r"^\d+(?:\.\d+)?\."])
    chapters = parser.extract(epub_path)

    assert [chapter["number"] for chapter in chapters] == [1, 2, 3, 4, 5]
    assert [chapter["title"] for chapter in chapters] == titles
