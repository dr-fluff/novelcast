# novelcast/engine/fanficfare_engine.py

from curses import raw

from .base import StoryEngine
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

class FanFicFareEngine(StoryEngine):

    def can_handle(self, url: str) -> bool:
        return True

    def fetch(self, url: str) -> dict:
        logger.info("FanFicFare download started", extra={"url": url})

        cmd = ["fanficfare", "--json-meta", url]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        raw = json.loads(result.stdout)

        epub_path = self._extract_epub_path(raw)

        return {
            "file_path": epub_path,
            "title": raw.get("title"),
            "author": raw.get("author"),
            "url": url,
        }
    
    def _extract_epub_path(self, raw: dict) -> str:
        possible_keys = [
            "output_filename",
            "outfile",
            "filename",
        ]

        for key in possible_keys:
            if key in raw and raw[key]:
                return raw[key]

        raise RuntimeError(f"Could not find EPUB path in response: {raw.keys()}")