import json
import logging
import subprocess
import sys
import selectors
import time
from urllib.parse import urlparse

from .base import StoryEngine

logger = logging.getLogger(__name__)

FFF_SUPPORTED_SITES = {"royalroad.com", "www.royalroad.com"}

IDLE_TIMEOUT_SECONDS = 300


class FanFicFareEngine(StoryEngine):

    FLAG_CONFIG = "--config"
    FLAG_METADATA = "--json-meta"
    FLAG_META_ONLY = "--meta-only"
    FLAG_NO_OUTPUT = "--no-output"
    FLAG_NON_INTERACTIVE = "--non-interactive"
    FLAG_PROGRESS = "--progressbar"

    def __init__(self, settings_repo, config_service):
        self.settings_repo = settings_repo
        self.config_service = config_service

    # -------------------------
    # ROUTING
    # -------------------------
    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in FFF_SUPPORTED_SITES if hostname else False

    # -------------------------
    # PUBLIC API
    # -------------------------
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        config_path = self.config_service.write_config()

        raw = self._run_fanficfare(
            url,
            config_path,
            progress_callback=progress_callback,
        )

        epub_path = self._extract_epub_path(raw)

        return {
            "title": raw.get("title"),
            "author": raw.get("author"),
            "url": url,
            "file_path": epub_path,
            "chapters": self._normalize_chapters(raw),
            "format": "epub",
            "raw": raw,
        }

    def check_updates(self, url: str) -> dict:
        config_path = self.config_service.write_config()

        raw = self._run_fanficfare(
            url,
            config_path,
            extra_flags=[self.FLAG_META_ONLY, self.FLAG_NO_OUTPUT],
        )

        return {
            "title": raw.get("title"),
            "author": raw.get("author"),
            "url": url,
            "raw": raw,
            "chapters": self._extract_chapter_details(raw),
        }

    def _extract_chapter_details(self, raw: dict) -> list[dict]:
        chapters_raw = raw.get("chapters") or raw.get("zchapters") or []

        chapters = []

        for idx, item in enumerate(chapters_raw, 1):
            num = idx
            title = None

            try:
                # ✔️ YOUR REAL FORMAT: [number, {title: ...}]
                if isinstance(item, (list, tuple)) and len(item) >= 2:

                    # number
                    if isinstance(item[0], int):
                        num = item[0]

                    # title (THIS is the important fix)
                    if isinstance(item[1], dict):
                        title = item[1].get("title")

                # fallback safety
                elif isinstance(item, dict):
                    title = item.get("title") or item.get("name")

                elif isinstance(item, str):
                    title = item

                chapters.append({
                    "number": num,
                    "title": title,
                    "selected": True,
                    "raw": item,
                })

            except Exception:
                logger.warning("Skipping bad chapter: %s", item)

        return chapters

    # -------------------------
    # CORE RUNNER
    # -------------------------
    def _run_fanficfare(self, url: str, config_path: str, progress_callback=None, extra_flags=None) -> dict:
        cmd = [
            sys.executable,
            "-m",
            "fanficfare.cli",
            self.FLAG_METADATA,
            self.FLAG_NON_INTERACTIVE,
            self.FLAG_CONFIG, config_path,
        ]

        if extra_flags:
            cmd.extend(extra_flags)

        cmd.append(url)

        logger.info("FanFicFare CMD=%s", " ".join(cmd))

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = process.communicate(timeout=300)

        stdout = stdout.decode(errors="replace")
        stderr = stderr.decode(errors="replace")

        logger.debug("FanFicFare returncode=%s", process.returncode)
        logger.debug("stderr tail=%s", stderr[-500:] if stderr else "(empty)")
        logger.debug("stdout size=%s chars", len(stdout))

        if process.returncode != 0:
            logger.error("FanFicFare failed: %s", stderr)
            raise RuntimeError(stderr or "FanFicFare failed")

        raw = self._parse_json_stdout(stdout)

        if not isinstance(raw, dict):
            raise RuntimeError("FanFicFare returned non-dict JSON")

        logger.debug("FanFicFare parsed keys=%s", list(raw.keys())[:30])

        return raw

    # -------------------------
    # JSON PARSER (robust)
    # -------------------------
    def _parse_json_stdout(self, stdout: str) -> dict:
        decoder = json.JSONDecoder()
        start = stdout.find("{")

        while start != -1:
            try:
                obj, _ = decoder.raw_decode(stdout[start:])
                if isinstance(obj, dict):
                    logger.debug("Selected JSON object at offset=%s", start)
                    return obj
            except json.JSONDecodeError:
                pass

            start = stdout.find("{", start + 1)

        logger.error("RAW STDOUT SAMPLE:\n%s", stdout[:2000])
        raise ValueError("No valid JSON object found in FanFicFare output")

    # -------------------------
    # CHAPTER NORMALIZATION (FIX YOUR BUG)
    # -------------------------
    def _normalize_chapters(self, raw: dict) -> list[int]:
        chapters = raw.get("chapters") or raw.get("zchapters") or []

        normalized = []

        for item in chapters:
            try:
                # FanFicFare sometimes returns:
                # [1, {...}] or tuples or strings
                if isinstance(item, int):
                    normalized.append(item)
                elif isinstance(item, (list, tuple)) and item:
                    if isinstance(item[0], int):
                        normalized.append(item[0])
                elif isinstance(item, str) and item.isdigit():
                    normalized.append(int(item))
            except Exception:
                logger.warning("Skipping bad chapter entry: %s", item)

        return normalized

    # -------------------------
    # METADATA EXTRACTION SAFE
    # -------------------------
    def _extract_metadata(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            return {}

        description = raw.get("description") or raw.get("summary")
        if isinstance(description, str):
            description = self._clean_html(description)

        return {
            "title": raw.get("title"),
            "author": raw.get("author"),
            "subtitle": raw.get("subtitle"),
            "description": description,
            "publish_year": self._parse_year(raw.get("datePublished")),
            "language": raw.get("language"),
            "series": raw.get("series"),
            "genres": self._split(raw.get("genre")),
            "tags": self._split(raw.get("subject_tags")),
        }

    def _split(self, value):
        if not value:
            return []
        if isinstance(value, str):
            return [v.strip() for v in value.split(",")]
        if isinstance(value, list):
            return value
        return []

    def _parse_year(self, value):
        if not value:
            return None
        try:
            return int(str(value)[:4])
        except Exception:
            return None

    def _clean_html(self, text: str) -> str:
        import re
        return re.sub(r"<.*?>", "", text)

    # -------------------------
    # EPUB PATH
    # -------------------------
    def _extract_epub_path(self, raw: dict) -> str:
        for key in ("output_filename", "outfile", "filename"):
            if raw.get(key):
                return raw[key]

        logger.error("No epub path in raw keys=%s", list(raw.keys()))
        raise RuntimeError("Missing epub output path")

    # -------------------------
    # OPTIONAL PROGRESS HOOK
    # -------------------------
    def _emit_progress(self, text, progress_callback, value=5):
        if not progress_callback:
            return value

        dots = text.count(".")
        if dots:
            value = min(90, value + dots)
            progress_callback("Processing", value)

        return value