import json
import logging
import selectors
import subprocess
import time
from urllib.parse import urlparse

from .base import StoryEngine

logger = logging.getLogger(__name__)

FFF_SUPPORTED_SITES = {
    "royalroad.com",
    "www.royalroad.com",
}


class FanFicFareEngine(StoryEngine):
    CMD = "fanficfare"
    FLAG_CONFIG = "--config"
    FLAG_METADATA = "--json-meta"
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
    # MAIN ENTRY
    # -------------------------
    def fetch(self, url: str, progress_callback=None) -> dict:
        logger.debug("FanFicFare fetch: %s", url)

        config_path = self.config_service.write_config()
        raw = self._run_fanficfare(url, config_path, progress_callback=progress_callback)

        epub_path = self._extract_epub_path(raw)

        return {
            "title": raw.get("title"),
            "author": raw.get("author"),
            "url": url,
            "file_path": epub_path,
            "chapters": None,
        }

    # -------------------------
    # EXECUTION LAYER
    # -------------------------
    def _run_fanficfare(self, url: str, config_path: str, progress_callback=None) -> dict:
        cmd = [
            self.CMD,
            self.FLAG_METADATA,
            self.FLAG_NON_INTERACTIVE,
            self.FLAG_PROGRESS,
            self.FLAG_CONFIG,
            config_path,
            url,
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError as e:
            raise RuntimeError("FanFicFare not installed") from e

        if progress_callback:
            progress_callback("Starting download", 5)

        stdout_chunks = []
        stderr_chunks = []
        progress_value = 5
        start = time.monotonic()

        selector = selectors.DefaultSelector()
        if process.stdout:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        if process.stderr:
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")

        while selector.get_map():
            if time.monotonic() - start > 120:
                process.kill()
                process.wait()
                selector.close()
                raise RuntimeError("FanFicFare timed out")

            for key, _ in selector.select(timeout=0.1):
                chunk = key.fileobj.read(4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue

                text = chunk.decode(errors="replace")
                if key.data == "stdout":
                    stdout_chunks.append(text)
                    progress_value = self._emit_progress_from_output(
                        text,
                        progress_callback,
                        progress_value,
                        is_stderr=False,
                    )
                else:
                    stderr_chunks.append(text)
                    progress_value = self._emit_progress_from_output(
                        text,
                        progress_callback,
                        progress_value,
                        is_stderr=True,
                    )

        selector.close()

        remaining_stdout, remaining_stderr = process.communicate()
        if remaining_stdout:
            text = remaining_stdout.decode(errors="replace")
            stdout_chunks.append(text)

        if remaining_stderr:
            text = remaining_stderr.decode(errors="replace")
            stderr_chunks.append(text)

        stdout = "".join(stdout_chunks).strip()
        stderr = "".join(stderr_chunks).strip()

        if progress_callback:
            progress_callback("Processing downloaded story", 95)

        if process.returncode != 0:
            logger.error("FanFicFare failed (stderr): %s", stderr)
            raise RuntimeError(stderr or "FanFicFare failed")

        if not stdout:
            logger.error("FanFicFare returned empty stdout (stderr=%s)", stderr)
            raise RuntimeError("FanFicFare returned no output")

        try:
            return self._parse_json_stdout(stdout)
        except ValueError:
            logger.error(
                "Invalid JSON from FanFicFare\nSTDOUT:\n%s\nSTDERR:\n%s",
                stdout[:2000],
                stderr[:2000],
            )
            raise RuntimeError("Invalid FanFicFare JSON output")

    # -------------------------
    # PARSING
    # -------------------------
    def _parse_json_stdout(self, stdout: str) -> dict:
        decoder = json.JSONDecoder()
        start = stdout.find("{")

        while start != -1:
            try:
                parsed, _ = decoder.raw_decode(stdout[start:])
            except json.JSONDecodeError:
                start = stdout.find("{", start + 1)
                continue

            if isinstance(parsed, dict):
                return parsed

            break

        raise ValueError("No JSON object found in FanFicFare stdout")

    def _emit_progress_from_output(
        self,
        text: str,
        progress_callback=None,
        progress_value: int = 5,
        is_stderr=False,
    ) -> int:
        if not progress_callback:
            return progress_value

        dot_count = text.count(".")
        if dot_count:
            progress_value = min(90, progress_value + dot_count)
            progress_callback("Downloading story data", progress_value)
            return progress_value

        if not is_stderr:
            return progress_value

        for line in text.splitlines():
            clean = line.strip()
            if clean:
                progress_callback("Downloading story data", progress_value)

        return progress_value

    def _extract_epub_path(self, raw: dict) -> str:
        for key in ("output_filename", "outfile", "filename"):
            if raw.get(key):
                return raw[key]

        raise RuntimeError(f"No epub path in response: {list(raw.keys())}")
