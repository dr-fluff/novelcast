# novelcast/engine/engine_fanficfare.py
import json
import logging
import os
import selectors
import subprocess
import sys
import time
from urllib.parse import urlparse

from .base import StoryEngine

logger = logging.getLogger(__name__)

FFF_SUPPORTED_SITES = {
    "royalroad.com",
    "www.royalroad.com",
}

# How long the process may be completely silent before we consider it hung.
# As long as FanFicFare keeps sending dots/lines, the timer resets.
IDLE_TIMEOUT_SECONDS = 300


class FanFicFareEngine(StoryEngine):
    FLAG_CONFIG = "--config"
    FLAG_METADATA = "--json-meta"
    FLAG_META_ONLY = "--meta-only"
    FLAG_NO_OUTPUT = "--no-output"
    FLAG_NON_INTERACTIVE = "--non-interactive"
    FLAG_PROGRESS = "--progressbar"
    FLAG_OUTPUT_DIR = "--output-dir"

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
    def fetch(self, url: str, progress_callback=None, output_dir = "/temp") -> dict:
        logger.debug("FanFicFare fetch: %s", url)

        config_path = self.config_service.write_config()
        raw = self._run_fanficfare(url, config_path, progress_callback=progress_callback)
        epub_path = self._extract_epub_path(raw)

        return {
            "title":      raw.get("title"),
            "author":     raw.get("author"),
            "url":        url,
            "file_path":  epub_path,
            "chapters":   None,
            "format":     "epub",
            "raw":        raw,
        }

    def check_updates(self, url: str) -> dict:
        logger.debug("FanFicFare update check: %s", url)

        config_path = self.config_service.write_config()
        raw = self._run_fanficfare(
            url,
            config_path,
            extra_flags=[self.FLAG_META_ONLY, self.FLAG_NO_OUTPUT],
        )

        return {
            "title":    raw.get("title"),
            "author":   raw.get("author"),
            "url":      url,
            "raw":      raw,
            "chapters": raw.get("chapters") or raw.get("zchapters") or [],
        }

    # -------------------------
    # EXECUTION LAYER
    # -------------------------
    def _run_fanficfare(
        self,
        url: str,
        config_path: str,
        progress_callback=None,
        extra_flags: list[str] | None = None,
    ) -> dict:
        cmd = [
            sys.executable,
            "-m",
            "fanficfare.cli",
            self.FLAG_METADATA,
            self.FLAG_NON_INTERACTIVE,
            self.FLAG_CONFIG, config_path,
        ]

        if progress_callback:
            cmd.append(self.FLAG_PROGRESS)

        if extra_flags:
            cmd.extend(extra_flags)

        cmd.append(url)

        logger.debug("Running: %s", " ".join(cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Let the OS buffer — avoids the busy-loop from bufsize=0
                # while still giving us line-level stderr for progress.
            )
        except FileNotFoundError as e:
            raise RuntimeError("FanFicFare not installed") from e

        if progress_callback:
            progress_callback("Starting download", 5)

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        progress_value = 5
        last_data_at = time.monotonic()  # reset every time we receive any bytes

        sel = selectors.DefaultSelector()
        if process.stdout:
            sel.register(process.stdout, selectors.EVENT_READ, "stdout")
        if process.stderr:
            sel.register(process.stderr, selectors.EVENT_READ, "stderr")

        try:
            while sel.get_map():
                idle_seconds = time.monotonic() - last_data_at
                if idle_seconds > IDLE_TIMEOUT_SECONDS:
                    process.kill()
                    process.wait()
                    raise RuntimeError(
                        f"FanFicFare hung — no output for {idle_seconds:.0f}s (url={url})"
                    )

                # Block up to 1 s so we check the idle clock regularly
                events = sel.select(timeout=1.0)

                for key, _ in events:
                    chunk = key.fileobj.read1(65536) if hasattr(key.fileobj, "read1") else key.fileobj.read(65536)

                    if not chunk:
                        sel.unregister(key.fileobj)
                        continue

                    # Any bytes at all = process is alive, reset the idle clock
                    last_data_at = time.monotonic()

                    text = chunk.decode(errors="replace")

                    if key.data == "stdout":
                        stdout_chunks.append(text)
                        progress_value = self._emit_progress(
                            text, progress_callback, progress_value, is_stderr=False
                        )
                    else:
                        stderr_chunks.append(text)
                        progress_value = self._emit_progress(
                            text, progress_callback, progress_value, is_stderr=True
                        )

        finally:
            sel.close()

        # Drain anything left after the selector loop ends
        try:
            remaining_out, remaining_err = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            remaining_out, remaining_err = process.communicate()

        if remaining_out:
            stdout_chunks.append(remaining_out.decode(errors="replace"))
        if remaining_err:
            stderr_chunks.append(remaining_err.decode(errors="replace"))

        stdout = "".join(stdout_chunks).strip()
        stderr = "".join(stderr_chunks).strip()

        if progress_callback:
            progress_callback("Processing downloaded story", 95)

        logger.debug(
            "FanFicFare exited %s | stderr_tail=%s",
            process.returncode,
            stderr[-300:] if stderr else "(empty)",
        )

        if process.returncode != 0:
            logger.error("FanFicFare failed (rc=%s) stderr:\n%s", process.returncode, stderr)
            raise RuntimeError(stderr or "FanFicFare failed")

        if not stdout:
            logger.error("FanFicFare empty stdout. stderr:\n%s", stderr)
            raise RuntimeError("FanFicFare returned no output")

        try:
            raw = self._parse_json_stdout(stdout)
            raw["format"] = "fanficfare"
            return raw
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

    def _emit_progress(
        self,
        text: str,
        progress_callback=None,
        progress_value: int = 5,
        is_stderr: bool = False,
    ) -> int:
        if not progress_callback:
            return progress_value

        dot_count = text.count(".")
        if dot_count:
            progress_value = min(90, progress_value + dot_count)
            progress_callback("Downloading story data", progress_value)
            return progress_value

        if is_stderr:
            for line in text.splitlines():
                if line.strip():
                    progress_callback("Downloading story data", progress_value)

        return progress_value

    def _extract_epub_path(self, raw: dict) -> str:
        for key in ("output_filename", "outfile", "filename"):
            if raw.get(key):
                return raw[key]

        raise RuntimeError(f"No epub path in FanFicFare response. Keys: {list(raw.keys())}")
