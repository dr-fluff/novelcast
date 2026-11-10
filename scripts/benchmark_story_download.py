#!/usr/bin/env python3
"""Measure FanFicFare proxy, metadata, download, and EPUB parsing time.

Examples:
    uv run python scripts/benchmark_story_download.py https://www.royalroad.com/fiction/123
    uv run python scripts/benchmark_story_download.py URL --mode update --epub /path/to/story.epub
    uv run python scripts/benchmark_story_download.py URL --mode download

The default mode only checks metadata. Update/download modes write temporary
files under the system temp directory and never modify the library or database.
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import logging
import re
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from novelcast.engine.engine_fanficfare import FanFicFareEngine
from novelcast.parser.epub_parser import EpubParser

_SENSITIVE_CONFIG_KEY_PARTS = ("password", "passwd", "email", "e-mail", "cookie", "session", "token", "secret", "username")


class Tee:
    def __init__(self, console, log_file):
        self.console = console
        self.log_file = log_file
        self.lock = threading.Lock()

    def write(self, text: str) -> int:
        with self.lock:
            self.console.write(text)
            self.log_file.write(text.replace("\r", "\n"))
            self.log_file.flush()
        return len(text)

    def flush(self) -> None:
        with self.lock:
            self.console.flush()
            self.log_file.flush()


def sanitized_ini_snapshot(path: Path) -> str:
    config = configparser.ConfigParser(interpolation=None, strict=False, allow_no_value=True)
    config.read(path, encoding="utf-8")
    lines = [f"Config SHA-256: {hashlib.sha256(path.read_bytes()).hexdigest()}"]

    for section in config.sections():
        lines.extend(("", f"[{section}]"))
        for key, value in config.items(section, raw=True):
            normalized_key = key.lower()
            if any(part in normalized_key for part in _SENSITIVE_CONFIG_KEY_PARTS):
                value = "<redacted>"
            elif value and "://" in value:
                parsed = urlsplit(value)
                if parsed.username or parsed.password:
                    host = parsed.hostname or ""
                    if parsed.port:
                        host = f"{host}:{parsed.port}"
                    value = urlunsplit((parsed.scheme, f"<redacted>@{host}", parsed.path, parsed.query, parsed.fragment))
            lines.append(f"{key}={value or ''}")

    return "\n".join(lines)


class ConfigFile:
    def __init__(self, path: Path):
        self.path = path

    def write_config(self, force: bool = False) -> str:
        return str(self.path)


def report_time(label: str, started: float) -> None:
    print(f"{label}: {time.perf_counter() - started:.2f}s")


def run_timed(
    label: str,
    operation: Callable,
    *args: Any,
    show_progress: bool = True,
    **kwargs: Any,
) -> tuple[Any, float, int | None]:
    started = time.perf_counter()
    stop_heartbeat = threading.Event()
    progress_lock = threading.Lock()
    progress_count: int | None = 0 if show_progress else None

    def report_progress(_message: str, _value: int | None = None) -> None:
        nonlocal progress_count
        with progress_lock:
            if progress_count is None:
                return
            progress_count += 1
            if progress_count % 10 == 0:
                print(f"\r{label}: {progress_count} network fetches", end="", flush=True)

    def heartbeat() -> None:
        while not stop_heartbeat.wait(15):
            with progress_lock:
                count = progress_count
            elapsed = time.perf_counter() - started
            count_text = f"{count} network fetches" if count is not None else "fetch count in FanFicFare debug log"
            print(f"\n{label} still running: {elapsed:.0f}s elapsed, {count_text}", flush=True)

    print(f"Starting {label}...", flush=True)
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    try:
        if show_progress:
            result = operation(*args, progress_callback=report_progress, **kwargs)
        else:
            result = operation(*args, **kwargs)
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
        if progress_count:
            print()

    elapsed = time.perf_counter() - started
    fetches = f"{progress_count} network fetches" if progress_count is not None else "fetch count in FanFicFare debug log"
    print(f"{label}: {elapsed:.2f}s ({fetches})", flush=True)
    return result, elapsed, progress_count


def run_benchmark(args) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    logging.getLogger("novelcast.engine.engine_fanficfare").setLevel(logging.DEBUG)
    with tempfile.TemporaryDirectory(prefix="novelcast-download-benchmark-") as temp_dir:
        engine = FanFicFareEngine(None, ConfigFile(args.config), download_dir=temp_dir)

        started = time.perf_counter()
        engine._ensure_proxy_available(args.url, str(args.config))
        report_time("Proxy preflight", started)

        metadata, _, _ = run_timed(
            "Metadata-only check (includes its proxy preflight)",
            engine.check_updates,
            args.url,
            show_progress=False,
        )
        print(f"Chapters reported by FanFicFare: {len(metadata.get('chapters') or [])}")

        if args.mode == "check":
            return 0

        if args.mode == "update":
            operation_label = "Incremental EPUB update"
            operation = engine.update_epub
            operation_args = (args.url, args.epub)
        else:
            operation_label = "Full story download"
            operation = engine.fetch
            operation_args = (args.url,)

        result, _, _ = run_timed(operation_label, operation, *operation_args)

        epub_path = Path(result["file_path"])
        if epub_path.is_file():
            print(f"EPUB size: {epub_path.stat().st_size / (1024 * 1024):.2f} MiB")

            patterns = args.pattern or [r"chapter", r"prologue", r"epilogue"]
            started = time.perf_counter()
            parsed = EpubParser(patterns=patterns).parse(result)
            report_time("EPUB parse and chapter extraction", started)
            print(f"Chapters extracted with supplied patterns: {len(parsed['chapters'])}")
        else:
            print(f"EPUB output was not found at {epub_path}; parsing was skipped")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="RoyalRoad story URL")
    parser.add_argument(
        "--mode",
        choices=("check", "update", "download"),
        default="check",
        help="check metadata only (default), update an existing EPUB, or download a full EPUB",
    )
    parser.add_argument("--epub", type=Path, help="Existing EPUB; required for --mode update")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/fanficfare.ini"),
        help="FanFicFare config file (default: config/fanficfare.ini)",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        help="Chapter-title regex for parse timing; may be supplied more than once",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("logs/story-download-benchmark.log"),
        help="Append benchmark output and sanitized config snapshot here",
    )
    args = parser.parse_args()

    if not args.config.is_file():
        parser.error(f"FanFicFare config not found: {args.config}")
    args.config = args.config.resolve()
    if args.mode == "update" and (not args.epub or not args.epub.is_file()):
        parser.error("--mode update requires an existing --epub file")

    args.log_file = args.log_file.expanduser().resolve()
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    original_stdout, original_stderr = sys.stdout, sys.stderr

    with args.log_file.open("a", encoding="utf-8", buffering=1) as log_file:
        sys.stdout = Tee(original_stdout, log_file)
        sys.stderr = Tee(original_stderr, log_file)
        try:
            print(f"\n=== Benchmark started {datetime.now().astimezone().isoformat(timespec='seconds')} ===")
            print(f"URL: {args.url}")
            print(f"Mode: {args.mode}")
            print(f"Config file: {args.config}")
            print("INI snapshot (credentials and session values redacted):")
            print(sanitized_ini_snapshot(args.config))
            print(f"Benchmark log: {args.log_file}")
            return run_benchmark(args)
        finally:
            sys.stdout, sys.stderr = original_stdout, original_stderr


if __name__ == "__main__":
    raise SystemExit(main())