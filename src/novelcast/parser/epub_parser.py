# novelcast/parser/epub_parser.py
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from novelcast.parser.base import BaseParser, Story


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _is_chapter(title: str, compiled: list[re.Pattern]) -> bool:
    """Return True if *title* matches any compiled chapter pattern."""
    if not title:
        return False
    return any(r.search(title) for r in compiled)


class EpubParser(BaseParser):
    def __init__(self, patterns: list[str] | None = None):
        self._patterns = _compile(patterns or [])
        
    def set_patterns(self, patterns: list[str]) -> None:
        """Update patterns (e.g., after DB reload)."""
        self._patterns = _compile(patterns)

    def parse(self, data: dict) -> Story:
        epub_path = Path(data["file_path"])
        chapters = self.extract(epub_path)
        cover = self._extract_cover(epub_path)
        raw_metadata = data.get("raw") if isinstance(data.get("raw"), dict) else data

        return {
            "title": data.get("title", raw_metadata.get("title", "Unknown")),
            "author": data.get("author") or raw_metadata.get("author"),
            "chapters": chapters,
            "cover_image": cover,
            "raw_metadata": raw_metadata,
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

                parsed_number = self._parse_chapter_number(title)
                if parsed_number is not None:
                    number = parsed_number
                else:
                    number += 1

                chapters.append(
                    {
                        "number": number,
                        "title": title or f"Chapter {number}",
                        "content": content,
                    }
                )

            return chapters

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
        title_tag = soup.find(["h1", "h2", "h3", "title"])
        if not title_tag:
            title_tag = soup.find("meta", attrs={"name": "chaptertitle"})
        if not title_tag:
            title_tag = soup.find("meta", attrs={"name": "chapterorigtitle"})
        if not title_tag:
            title_tag = soup.find("meta", attrs={"name": "chaptertoctitle"})

        if title_tag and title_tag.name == "meta":
            title = title_tag.get("content", "").strip()
        else:
            title = title_tag.get_text(strip=True) if title_tag else ""

        body = soup.find("body")
        if not body:
            content = soup.get_text(separator="\n", strip=True)
        else:
            content = "".join(str(child) for child in body.contents).strip()

        return title, content

    def _parse_chapter_number(self, title: str) -> int | None:
        if not title:
            return None

        # Try to extract a number from any of the chapter patterns
        for compiled_pattern in self._patterns:
            match = compiled_pattern.search(title)
            if match and match.groups():
                try:
                    return int(match.group(1))
                except (IndexError, ValueError):
                    pass

        return None