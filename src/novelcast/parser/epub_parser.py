# novelcast/parser/epub_parser.py

import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from novelcast.parser.base import BaseParser, Story


# ── Built-in chapter patterns ──────────────────────────────────────────────
# These cover the most common web fiction / RoyalRoad naming conventions.
# Extra patterns can be added at runtime via the DB (see ChapterFilterService).
#
# Format: plain regex strings, case-insensitive flag applied automatically.
#
# RoyalRoad examples covered:
#   "Chapter 1"                              →  \bchapter\s*\d+
#   "Chapter 4 Exploration"                  →  \bchapter\s*\d+
#   "Chapter: 1 - New Beginnings"            →  \bchapter\s*:?\s*\d+
#   "Chapter ???"                            →  \bchapter\s*\?+
#   "Chapter 1: Strange Business"            →  \bchapter\s*\d+
#   "1.1"  /  "3.10"                         →  ^\[?\d+\.\d+
#   "1 - Vivisari"                           →  ^\[?\d+\s*[-–]
#   "Part 9 (3.10)"  /  "Part 67: Running"  →  \bpart\s*\d+
#   "Prologue"                               →  \bprologue\b
#   "Interlude - text"                       →  \binterlude\b
#   "Bestiary Interlude : Hydra"             →  \binterlude\b
#   "Glossary"                               →  \bglossary\b
#   "The Path of Ascension Chapter 1"        →  \bchapter\s*\d+
#   "[1 - Breakfast at Night](url)"          →  ^\[?\d+\s*[-–]
#   "[1. Aine ~ Garden](url)"                →  ^\[?\d+\.
#   "[Chapter 0 - Four who heard](url)"      →  \bchapter\s*\d+
#
# Patreon examples covered:
#   "Amazon Apocalypse 7: Chapter 77"        →  \bchapter\s*\d+
#   "Journey to Veresavir - Chapter 55"      →  \bchapter\s*\d+
#   "In Search of Harmony 26 - No, No..."   →  \w.*\s+\d+\s*[-–]
DEFAULT_PATTERNS: list[str] = [
    r"\bchapter\s*:?\s*\d+",       # Chapter 1 / Chapter: 1 / Chapter 930
    r"\bchapter\s*\?+",            # Chapter ???
    r"\bch\.?\s*\d+",              # Ch. 42 / Ch42
    r"^\[?\d+\.\d+",               # 1.1 / 3.10 / [1.1]
    r"^\[?\d+\s*[-–]",             # 1 - Vivisari / [1 - Breakfast...]
    r"^\[?\d+\.",                   # 1. Aine ~ Garden / [1. ...]
    r"\bpart\s*\d+",               # Part 1 / Part 9 (3.10)
    r"\bpart\s+[ivxlcdm]+\b",      # Part IV (Roman numerals)
    r"\bprologue\b",               # Prologue / The Prologue
    r"\bepilogue\b",               # Epilogue
    r"\binterlude\b",              # Interlude / Bestiary Interlude : Hydra
    r"\bafterword\b",              # Afterword
    r"\bglossary\b",               # Glossary
    r"\bappendix\b",               # Appendix
    r"\bcover\b",                  # Cover page
    r"\bby\s+\w+",                 # "Azarinth Healer by Rhaegar"
    r"\w.*\s+\d+\s*[-–]",         # "In Search of Harmony 26 - ..."
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _is_chapter(title: str, compiled: list[re.Pattern]) -> bool:
    """Return True if *title* matches any compiled chapter pattern."""
    if not title:
        return False
    return any(r.search(title) for r in compiled)


class EpubParser(BaseParser):
    """
    Parses an EPUB file into a Story dict.

    extra_patterns: additional regex strings loaded from the DB at call time.
                    Pass them in via ChapterFilterService before calling parse().
    """

    def __init__(self, extra_patterns: list[str] | None = None):
        self._patterns = _compile(DEFAULT_PATTERNS + (extra_patterns or []))

    def set_extra_patterns(self, patterns: list[str]) -> None:
        """Hot-reload patterns (e.g. after a DB query returns user-defined ones)."""
        self._patterns = _compile(DEFAULT_PATTERNS + patterns)

    def parse(self, data: dict) -> Story:
        epub_path = Path(data["file_path"])
        chapters = self.extract(epub_path)
        cover = self._extract_cover(epub_path)

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters,
            "cover_image": cover,
        }

    def extract(self, epub_path: Path) -> list[dict]:
        if not epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        with ZipFile(epub_path, "r") as epub:
            rootfile_path = self._find_rootfile_path(epub)
            manifest, spine = self._parse_package_document(epub.read(rootfile_path))
            base_path = Path(rootfile_path).parent

            chapters = []
            number = 0  # only incremented for recognised chapters

            for itemref in spine:
                href = manifest.get(itemref)
                if not href:
                    continue

                item_path = (base_path / href).as_posix()
                try:
                    item_data = epub.read(item_path)
                except KeyError:
                    continue

                title, content = self._parse_chapter(item_data)

                if not _is_chapter(title, self._patterns):
                    continue  # announcement / ad / non-story item — skip

                number += 1
                chapters.append(
                    {
                        "number": number,
                        "title": title or f"Chapter {number}",
                        "content": content,
                    }
                )

            return chapters

    # ── private helpers ────────────────────────────────────────────────────

    def _extract_cover(self, epub_path: Path) -> bytes | None:
        try:
            with ZipFile(epub_path, "r") as epub:
                rootfile_path = self._find_rootfile_path(epub)
                package_data = epub.read(rootfile_path)
                root = ET.fromstring(package_data)

                cover_id = None
                for meta in root.iter():
                    if meta.tag.endswith("meta") and meta.attrib.get("name") == "cover":
                        cover_id = meta.attrib.get("content")

                if cover_id:
                    for item in root.iter():
                        if item.tag.endswith("item") and item.attrib.get("id") == cover_id:
                            href = item.attrib.get("href")
                            if href:
                                base = Path(rootfile_path).parent
                                return epub.read((base / href).as_posix())

                for name in epub.namelist():
                    if "cover" in name.lower() and name.lower().endswith((".jpg", ".jpeg", ".png")):
                        return epub.read(name)
        except Exception:
            return None

        return None

    def _find_rootfile_path(self, epub: ZipFile) -> str:
        try:
            container_data = epub.read("META-INF/container.xml")
        except KeyError as exc:
            raise RuntimeError("Invalid EPUB: META-INF/container.xml missing") from exc

        root = ET.fromstring(container_data)
        for elem in root.iter():
            if elem.tag.endswith("rootfile"):
                path = elem.attrib.get("full-path")
                if path:
                    return path

        raise RuntimeError("Invalid EPUB: rootfile not found in container.xml")

    def _parse_package_document(self, package_data: bytes):
        root = ET.fromstring(package_data)
        manifest: dict[str, str] = {}
        spine: list[str] = []

        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag == "item" and "id" in elem.attrib and "href" in elem.attrib:
                manifest[elem.attrib["id"]] = elem.attrib["href"]
            if tag == "itemref" and "idref" in elem.attrib:
                spine.append(elem.attrib["idref"])

        return manifest, spine

    def _parse_chapter(self, item_data: bytes) -> tuple[str, str]:
        soup = BeautifulSoup(item_data, "html.parser")
        title_tag = soup.find(["h1", "h2", "title"])
        title = title_tag.get_text(strip=True) if title_tag else ""

        body = soup.find("body")
        if not body:
            content = soup.get_text(separator="\n", strip=True)
        else:
            content = "".join(str(child) for child in body.contents).strip()

        return title, content