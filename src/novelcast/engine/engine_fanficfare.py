# novelcast/engine/engine_fanficfare.py
import configparser
import json
import logging
import queue
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .base import FORMAT_EPUB, KEY_AUTHOR, KEY_RAW, KEY_TITLE, StoryEngine, make_result

logger = logging.getLogger(__name__)

FFF_SUPPORTED_SITES = {"royalroad.com", "www.royalroad.com"}

# Kill the process if no output activity (not even a progress dot) for this long.
IDLE_TIMEOUT_SECONDS = 300
# Hard ceiling regardless of activity — safety net in case dots never stop.
MAX_TOTAL_SECONDS = 3600

# Pre-flight check of the FlareSolverr-compatible proxy (Anubis shim / FlareSolverr).
PROXY_CHECK_TIMEOUT_SECONDS = 3
# Values of use_flaresolverr_proxy that mean "don't use the proxy".
_PROXY_OFF_VALUES = ("", "false", "0", "no", "off")

# --- FanFicFare's raw JSON field names (their schema, not ours) ---
# These are what fanficfare.cli --json-meta actually emits. Kept as constants
# so a typo raises a clear "unknown name" at import/lint time instead of
# silently returning None from raw.get(...).
FFF_TITLE = "title"
FFF_AUTHOR = "author"
FFF_SUBTITLE = "subtitle"
FFF_DESCRIPTION = "description"
FFF_SUMMARY = "summary"
FFF_DATE_PUBLISHED = "datePublished"
FFF_LANGUAGE = "language"
FFF_SERIES = "series"
FFF_GENRE = "genre"
FFF_SUBJECT_TAGS = "subject_tags"
FFF_OUTPUT_FILENAME = "output_filename"
FFF_OUTFILE = "outfile"
FFF_FILENAME = "filename"
FFF_CHAPTERS = "chapters"
FFF_ZCHAPTERS = "zchapters"
FFF_NAME = "name"

# --- Our own chapter-dict shape (returned by _extract_chapter_details) ---
# "title" and "raw" reuse base.KEY_TITLE/KEY_RAW since the string is
# genuinely the same field concept; "number"/"selected" are chapter-only.
CHAPTER_KEY_NUMBER = "number"
CHAPTER_KEY_SELECTED = "selected"


class ProxyUnavailableError(RuntimeError):
    """The configured FlareSolverr-compatible proxy isn't reachable.

    Raised *before* FanFicFare is launched. Subclasses RuntimeError so existing
    `except RuntimeError` / `except Exception` handlers keep working.
    """


class FanFicFareEngine(StoryEngine):
    FLAG_CONFIG = "--config"
    FLAG_METADATA = "--json-meta"
    FLAG_META_ONLY = "--meta-only"
    FLAG_NO_OUTPUT = "--no-output"
    FLAG_NON_INTERACTIVE = "--non-interactive"
    FLAG_PROGRESS = "--progressbar"
    FLAG_UPDATE_EPUB = "--update-epub"

    def __init__(self, settings_repo, config_service, download_dir: str):
        self.settings_repo = settings_repo
        self.config_service = config_service
        self.download_dir = Path(download_dir).resolve()
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in FFF_SUPPORTED_SITES if hostname else False

    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        config_path = self.config_service.write_config()

        raw = self._run_fanficfare(
            url,
            config_path,
            progress_callback=progress_callback,
        )

        epub_path = self._extract_epub_path(raw)

        return make_result(
            title=raw.get(FFF_TITLE),
            author=raw.get(FFF_AUTHOR),
            url=url,
            file_path=epub_path,
            chapters=self._extract_chapter_details(raw),
            format=FORMAT_EPUB,
            story_site_id=self._extract_story_site_id(url, raw),
            raw=raw,
        )

    def check_updates(self, url: str) -> dict:
        config_path = self.config_service.write_config()

        raw = self._run_fanficfare(
            url,
            config_path,
            extra_flags=[self.FLAG_META_ONLY, self.FLAG_NO_OUTPUT],
        )

        return make_result(
            title=raw.get(FFF_TITLE),
            author=raw.get(FFF_AUTHOR),
            url=url,
            chapters=self._extract_chapter_details(raw),
            story_site_id=self._extract_story_site_id(url, raw),
            raw=raw,
        )

    def update_epub(self, url: str, existing_epub: str | Path, progress_callback=None) -> dict:
        existing_path = Path(existing_epub).resolve()
        if not existing_path.is_file():
            return self.fetch(url, progress_callback=progress_callback)

        staging_dir = Path(tempfile.mkdtemp(prefix=".fanficfare-update-", dir=self.download_dir))
        staged_epub = staging_dir / existing_path.name

        try:
            shutil.copy2(existing_path, staged_epub)
            config_path = self.config_service.write_config()
            raw = self._run_fanficfare(
                url,
                config_path,
                progress_callback=progress_callback,
                extra_flags=[self.FLAG_UPDATE_EPUB],
                input_path=str(staged_epub),
            )
            result = make_result(
                title=raw.get(FFF_TITLE),
                author=raw.get(FFF_AUTHOR),
                url=url,
                file_path=self._extract_epub_path(raw),
                chapters=self._extract_chapter_details(raw),
                format=FORMAT_EPUB,
                story_site_id=self._extract_story_site_id(url, raw),
                raw=raw,
            )
        except Exception:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

        return result

    def _extract_chapter_details(self, raw: dict) -> list[dict]:
        chapters_raw = raw.get(FFF_CHAPTERS) or raw.get(FFF_ZCHAPTERS) or []

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
                        title = item[1].get(FFF_TITLE)

                # fallback safety
                elif isinstance(item, dict):
                    title = item.get(FFF_TITLE) or item.get(FFF_NAME)

                elif isinstance(item, str):
                    title = item

                chapters.append(
                    {
                        CHAPTER_KEY_NUMBER: num,
                        KEY_TITLE: title,
                        CHAPTER_KEY_SELECTED: True,
                        KEY_RAW: item,
                    }
                )

            except Exception:
                logger.warning("Skipping bad chapter: %s", item)

        return chapters

    # ── pre-flight: is the FlareSolverr-compatible proxy up? ─────────────

    def _proxy_settings(self, url: str, config_path: str):
        """Read the generated ini and return (protocol, address, port) if this
        URL is routed through the FlareSolverr proxy, else None.

        Reads the same file FanFicFare reads, so the check can never drift from
        what the GUI settings actually produced. A site section (e.g. the
        RoyalRoad one) wins over [defaults].
        """
        parser = configparser.ConfigParser(interpolation=None, strict=False, allow_no_value=True)
        parser.read(config_path, encoding="utf-8")

        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        sections = [s for s in parser.sections() if s.lower().removeprefix("www.") == host]
        sections.append("defaults")

        def lookup(key: str, default: str) -> str:
            for section in sections:
                if parser.has_option(section, key):
                    value = parser.get(section, key)
                    if value and value.strip():
                        return value.strip()
            return default

        if lookup("use_flaresolverr_proxy", "false").lower() in _PROXY_OFF_VALUES:
            return None

        protocol = lookup("flaresolverr_proxy_protocol", "http").lower()
        address = lookup("flaresolverr_proxy_address", "localhost")
        port = lookup("flaresolverr_proxy_port", "8191")
        return protocol, address, port

    def _ensure_proxy_available(self, url: str, config_path: str) -> None:
        """Fail fast, with one clear log line, if the proxy FanFicFare is about
        to use isn't answering. Any HTTP response (even a 404) counts as up."""
        try:
            proxy = self._proxy_settings(url, config_path)
        except Exception:
            logger.debug("Could not read proxy settings from %s; skipping proxy check", config_path, exc_info=True)
            return

        if proxy is None:
            return

        protocol, address, port = proxy
        if protocol not in ("http", "https"):
            return  # e.g. socks5 can't be probed with a plain HTTP GET

        target = f"{protocol}://{address}:{port}/"

        # Bypass any HTTP(S)_PROXY env vars; this is a direct liveness probe.
        handlers = [urllib.request.ProxyHandler({})]
        if protocol == "https":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # liveness only, nothing is sent
            handlers.append(urllib.request.HTTPSHandler(context=context))
        opener = urllib.request.build_opener(*handlers)

        try:
            opener.open(target, timeout=PROXY_CHECK_TIMEOUT_SECONDS).close()
        except urllib.error.HTTPError:
            return  # it answered over HTTP, so it's up
        except Exception as exc:
            detail = getattr(exc, "reason", None) or exc
            message = (
                f"Proxy unreachable at {target.rstrip('/')} "
                f"({detail}). Is the Anubis shim / FlareSolverr running?"
            )
            raise ProxyUnavailableError(message) from exc

    def _run_fanficfare(self, url, config_path, progress_callback=None, extra_flags=None, input_path=None):

        self._ensure_proxy_available(url, config_path)

        cmd = [
            sys.executable,
            "-m",
            "fanficfare.cli",
            self.FLAG_METADATA,
            self.FLAG_NON_INTERACTIVE,
            self.FLAG_PROGRESS,  # emits one "." per network fetch to stdout — our liveness signal
            self.FLAG_CONFIG,
            config_path,
        ]

        if extra_flags:
            cmd.extend(extra_flags)

        cmd.append(input_path or url)

        logger.info("FanFicFare CMD=%s", " ".join(cmd))

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.download_dir),
            bufsize=0,
        )

        stdout, stderr, dot_count = self._stream_with_idle_timeout(process, url, cmd, progress_callback)

        logger.debug("FanFicFare returncode=%s dots_seen=%d", process.returncode, dot_count)
        logger.debug("stderr tail=%s", stderr[-500:] if stderr else "(empty)")
        logger.debug("stdout size=%s chars", len(stdout))

        if process.returncode != 0:
            stderr_text = stderr.strip()

            logger.debug(
                "FanFicFare failed: returncode=%s stderr=%s",
                process.returncode,
                stderr_text[-2000:] if stderr_text else "(empty)",
            )

            raise RuntimeError(
                stderr_text[-2000:] if stderr_text else "FanFicFare failed"
            )

        raw = self._parse_json_stdout(stdout)

        if not isinstance(raw, dict):
            raise RuntimeError("FanFicFare returned non-dict JSON")

        logger.debug("FanFicFare parsed keys=%s", list(raw.keys())[:30])

        return raw

    def _stream_with_idle_timeout(self, process, url, cmd, progress_callback=None):
        """Read stdout incrementally instead of blocking on communicate(), so a
        --progressbar dot resets the idle clock. This kills the process only
        when it's genuinely stuck (no output at all for IDLE_TIMEOUT_SECONDS),
        not just because a big story takes a while — as long as dots keep
        coming, it keeps waiting, up to MAX_TOTAL_SECONDS as a hard ceiling.

        NOTE: assumes --progressbar writes a single unbuffered "." per fetch
        with no other single-byte output competing with it on stdout. Worth
        confirming against your installed fanficfare version — if it batches
        output differently this dot-counting logic may need adjusting.
        """
        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        activity_q: queue.Queue = queue.Queue()

        def read_stdout():
            try:
                for chunk in iter(lambda: process.stdout.read(1), b""):
                    stdout_chunks.append(chunk)
                    activity_q.put(chunk)
            finally:
                activity_q.put(None)  # sentinel: stdout closed

        def read_stderr():
            try:
                for chunk in iter(lambda: process.stderr.read(4096), b""):
                    stderr_chunks.append(chunk)
            except Exception:
                pass

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        started = time.monotonic()
        dot_count = 0
        timed_out_reason = None

        while True:
            try:
                item = activity_q.get(timeout=IDLE_TIMEOUT_SECONDS)
            except queue.Empty:
                timed_out_reason = f"no output for {IDLE_TIMEOUT_SECONDS}s (fetch appears stuck)"
                break

            if item is None:
                break  # stdout closed — process is done producing output

            if item == b".":
                dot_count += 1
                self._emit_progress("." * dot_count, progress_callback)

            if time.monotonic() - started > MAX_TOTAL_SECONDS:
                timed_out_reason = f"exceeded hard cap of {MAX_TOTAL_SECONDS}s"
                break

        if timed_out_reason:
            process.kill()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.error("FanFicFare process did not exit after kill(): pid=%s", process.pid)
            stderr_thread.join(timeout=5)

            stderr_text = b"".join(stderr_chunks).decode(errors="replace")
            logger.error(
                "FanFicFare killed: %s. url=%s cmd=%s dots_seen=%d\nstderr tail=%s",
                timed_out_reason,
                url,
                " ".join(cmd),
                dot_count,
                stderr_text[-1000:] if stderr_text else "(empty)",
            )
            raise RuntimeError(f"FanFicFare timed out fetching {url} ({timed_out_reason}) — process was killed")

        process.wait(timeout=30)
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        stdout = b"".join(stdout_chunks).decode(errors="replace")
        stderr = b"".join(stderr_chunks).decode(errors="replace")
        return stdout, stderr, dot_count

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

    def _extract_metadata(self, raw: dict) -> dict:
        """NOTE: not called anywhere else in this file — confirm something
        outside this module still uses it before relying on it, or it may be
        dead code left over from an earlier version."""
        if not isinstance(raw, dict):
            return {}

        description = raw.get(FFF_DESCRIPTION) or raw.get(FFF_SUMMARY)
        if isinstance(description, str):
            description = self._clean_html(description)

        return {
            KEY_TITLE: raw.get(FFF_TITLE),
            KEY_AUTHOR: raw.get(FFF_AUTHOR),
            "subtitle": raw.get(FFF_SUBTITLE),
            "description": description,
            "publish_year": self._parse_year(raw.get(FFF_DATE_PUBLISHED)),
            "language": raw.get(FFF_LANGUAGE),
            "series": raw.get(FFF_SERIES),
            "genres": self._split(raw.get(FFF_GENRE)),
            "tags": self._split(raw.get(FFF_SUBJECT_TAGS)),
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

    def _extract_epub_path(self, raw: dict) -> str:
        for key in (FFF_OUTPUT_FILENAME, FFF_OUTFILE, FFF_FILENAME):
            if raw.get(key):
                return str((self.download_dir / raw[key]).resolve())
        logger.error("No epub path in raw keys=%s", list(raw.keys()))
        raise RuntimeError("Missing epub output path")

    def _emit_progress(self, text, progress_callback, value=5):
        if not progress_callback:
            return value

        dots = text.count(".")
        if dots:
            value = min(90, value + dots)
            progress_callback("Processing", value)

        return value

    def _extract_story_site_id(self, url: str, raw: dict) -> str | None:
        import re

        # Prefer clean numeric ID from URL
        match = re.search(r"/fiction/(\d+)", url)
        if match:
            return match.group(1)

        # Fallback: strip prefix from output_filename
        output_filename = raw.get(FFF_OUTPUT_FILENAME) or ""
        match = re.search(r"-([a-z]+_(\d+))\.epub$", output_filename)
        if match:
            return match.group(2)  # just the number

        return None