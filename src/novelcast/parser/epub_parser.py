# novelcast/parser/epub_parser.py
import re
from pathlib import Path
from zipfile import ZipFile
import logging
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from novelcast.parser.base import BaseParser, Story

logger = logging.getLogger(__name__)

def _compile(patterns: list[str]) -> list[re.Pattern]:
    compiled = []

    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            logger.exception("Invalid chapter regex pattern: %r", pattern)

    logger.debug("Compiled %d/%d chapter patterns", len(compiled), len(patterns))
    return compiled


def _is_chapter(title: str, compiled: list[re.Pattern]) -> bool:
    if not title:
        logger.debug("Empty title cannot be chapter")
        return False

    for regex in compiled:
        if regex.search(title):
            logger.debug("Chapter match: %r matched %r",title,regex.pattern)
            return True

    logger.debug("No chapter pattern matched: %r",title)

    return False


class EpubParser(BaseParser):
    def __init__(self, patterns: list[str] | None = None):
        self._patterns = _compile(patterns or [])

        logger.debug(
            "EpubParser initialized with %d chapter patterns",
            len(self._patterns)
        )
        
    def set_patterns(self, patterns: list[str]) -> None:
        """Update patterns (e.g., after DB reload)."""
        self._patterns = _compile(patterns)

        logger.info(
            "Chapter patterns updated. Loaded %d patterns",
            len(self._patterns)
        )

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
        logger.info("Extracting EPUB: %s", epub_path)
        if not epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        with ZipFile(epub_path, "r") as epub:
            self._validate_epub(epub, epub_path)
            root_file_path = self._find_root_file_path(epub)
            manifest, spine = self._parse_package_document(epub.read(root_file_path))
            logger.debug(
                "EPUB package loaded. Manifest items: %d, Spine items: %d",
                len(manifest),
                len(spine)
            )
            base_path = Path(root_file_path).parent

            chapters = []
            number = 0  # only incremented for recognized chapters

            for itemref in spine:
                href = manifest.get(itemref)
                if not href:
                    logger.warning("Spine item %s has no manifest entry",itemref)
                    continue

                item_path = (base_path / href).as_posix()
                try:
                    item_data = epub.read(item_path)
                except KeyError:
                    logger.warning("Missing EPUB resource: %s",item_path)
                    continue

                title, content = self._parse_chapter(item_data)
                logger.debug(
                    "Parsed EPUB item %s -> title=%r content_length=%d",
                    item_path,
                    title,
                    len(content)
                )

                if not _is_chapter(title, self._patterns):
                    logger.debug(
                        "Skipping non-chapter item: %r",
                        title
                    )
                    continue 

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

            if not chapters:
                logger.warning("No chapters extracted from EPUB: %s",epub_path)
            else:
                logger.info("Extracted %d chapters from %s",len(chapters),epub_path)

            return chapters

    def _extract_cover(self, epub_path: Path) -> bytes | None:
        try:
            with ZipFile(epub_path, "r") as epub:
                root_file_path = self._find_root_file_path(epub)
                package_data = epub.read(root_file_path)
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
                                base = Path(root_file_path).parent
                                return epub.read((base / href).as_posix())

                for name in epub.namelist():
                    if "cover" in name.lower() and name.lower().endswith((".jpg", ".jpeg", ".png")):
                        return epub.read(name)
        except Exception:
            logger.exception("Failed extracting cover from %s",epub_path)
            return None

        return None

    def _find_root_file_path(self, epub: ZipFile) -> str:
        try:
            container_data = epub.read("META-INF/container.xml")

        except KeyError as exc:
            raise RuntimeError(
                "Invalid EPUB: META-INF/container.xml missing"
            ) from exc

        try:
            root = ET.fromstring(container_data)

        except ET.ParseError as exc:
            raise RuntimeError(
                "Invalid EPUB: container.xml contains invalid XML"
            ) from exc

        rootfiles = [
            elem
            for elem in root.iter()
            if elem.tag.endswith("rootfile")
        ]

        if not rootfiles:
            raise RuntimeError(
                "Invalid EPUB: container.xml has no rootfile entries"
            )

        for elem in rootfiles:
            path = elem.attrib.get("full-path")

            if path:
                logger.debug(
                    "EPUB root file found: %s",
                    path
                )
                return path

        raise RuntimeError(
            "Invalid EPUB: rootfile exists but has no full-path attribute"
        )

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
        try:
            soup = BeautifulSoup(item_data, "html.parser")
        except Exception:
            logger.exception("Failed parsing XHTML chapter")
            return "", ""
        
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
    
    def _validate_epub(self, epub: ZipFile, epub_path: Path) -> None:
        """Basic EPUB integrity checks."""

        required_files = [
            "META-INF/container.xml",
        ]

        logger.debug("Validating EPUB: %s", epub_path)

        names = set(epub.namelist())

        for required in required_files:
            if required not in names:
                raise RuntimeError(
                    f"Invalid EPUB '{epub_path}': missing required file '{required}'. "
                    f"Available META-INF files: "
                    f"{[n for n in names if n.startswith('META-INF')]}"
                )

        try:
            container = epub.read("META-INF/container.xml")
        except Exception as exc:
            raise RuntimeError(
                f"Invalid EPUB '{epub_path}': unable to read META-INF/container.xml"
            ) from exc

        try:
            root = ET.fromstring(container)
        except ET.ParseError as exc:
            raise RuntimeError(
                f"Invalid EPUB '{epub_path}': malformed container.xml XML"
            ) from exc

        rootfiles = [
            elem
            for elem in root.iter()
            if elem.tag.endswith("rootfile")
        ]

        if not rootfiles:
            raise RuntimeError(
                f"Invalid EPUB '{epub_path}': container.xml contains no <rootfile>"
            )

        logger.debug(
            "EPUB validation passed: %s",
            epub_path
        )