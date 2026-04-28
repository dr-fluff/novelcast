# novelcast/parser/epub_parser.py

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from novelcast.parser.base import BaseParser, Story


class EpubParser(BaseParser):

    def parse(self, data: dict) -> Story:
        epub_path = Path(data["file_path"])
        chapters = self.extract(epub_path)

        return {
            "title": data.get("title", "Unknown"),
            "author": data.get("author"),
            "chapters": chapters
        }

    def extract(self, epub_path: Path):
        if not epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        with ZipFile(epub_path, "r") as epub:
            rootfile_path = self._find_rootfile_path(epub)
            manifest, spine = self._parse_package_document(epub.read(rootfile_path))
            base_path = Path(rootfile_path).parent

            chapters = []
            for number, itemref in enumerate(spine, start=1):
                href = manifest.get(itemref)
                if not href:
                    continue

                item_path = (base_path / href).as_posix()
                try:
                    item_data = epub.read(item_path)
                except KeyError:
                    continue

                title, content = self._parse_chapter(item_data)
                chapters.append(
                    {
                        "number": number,
                        "title": title or f"Chapter {number}",
                        "content": content,
                    }
                )

            return chapters

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
        manifest = {}
        spine = []

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