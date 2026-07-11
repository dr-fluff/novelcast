# novelcast/core/logging.py

from __future__ import annotations

import json
import logging
import re
import sys
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Deque

from novelcast.core import setting_keys
from novelcast.core.defaults import (
    LOGGING_DEFAULTS,
    LOGGING_FILE,
    LOGGING_LEVEL,
    LOGGING_MAX_AMOUNT_OF_FILES,
    LOGGING_MAX_BYTES,
    LOGGING_NOISY_LOGGERS,
    LOGGING_TAIL_BUFFER_SIZE,
)

logger = logging.getLogger(__name__)


request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

_TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9:_-]+")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*")


def redact(value: str) -> str:
    if not isinstance(value, str):
        return value
    value = _TOKEN_RE.sub("bot***:***", value)
    value = _BEARER_RE.sub("Bearer ***", value)
    return value


def _schema_default(key: str):
    return LOGGING_DEFAULTS[key]["default"]


@dataclass
class LogConfig:
    level: str = field(default_factory=lambda: _schema_default(LOGGING_LEVEL).upper())
    file_path: str = field(default_factory=lambda: _schema_default(LOGGING_FILE))
    max_bytes: int = field(default_factory=lambda: _schema_default(LOGGING_MAX_BYTES))
    noisy_loggers: list[str] = field(default_factory=lambda: json.loads(_schema_default(LOGGING_NOISY_LOGGERS)))
    tail_buffer_size: int = field(default_factory=lambda: _schema_default(LOGGING_TAIL_BUFFER_SIZE))
    max_files: int = field(default_factory=lambda: _schema_default(LOGGING_MAX_AMOUNT_OF_FILES))

    @classmethod
    def from_settings_service(cls, svc) -> "LogConfig":
        cfg = cls()

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.LEVEL):
            cfg.level = v.upper()

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.FILE):
            cfg.file_path = v

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.MAX_BYTES):
            with _swallow():
                cfg.max_bytes = int(v)

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.NOISY_LOGGERS):
            with _swallow():
                cfg.noisy_loggers = json.loads(v)

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.TAIL_BUFFER_SIZE):
            with _swallow():
                cfg.tail_buffer_size = int(v)

        if v := _get(svc, setting_keys.LOGGING_SETTINGS.MAX_AMOUNT_OF_FILES):
            with _swallow():
                cfg.max_files = int(v)

        return cfg

    @classmethod
    def from_app_config(cls, app_config) -> "LogConfig":
        cfg = cls()
        cfg.level = getattr(app_config, "log_level", _schema_default(LOGGING_LEVEL)).upper()
        cfg.file_path = getattr(app_config, "log_file", _schema_default(LOGGING_FILE)) or _schema_default(LOGGING_FILE)
        return cfg

    @classmethod
    def console_only(cls) -> "LogConfig":
        cfg = cls()
        cfg.file_path = ""
        return cfg


def _get(svc, dotted_key: str, default=None) -> str | None:
    try:
        value = svc.get(dotted_key, default=default).value
    except Exception:
        return None
    return value if value not in (None, "") else None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": request_id_ctx.get(),
        }

        if hasattr(record, "extra_data"):
            for k, v in record.extra_data.items():
                log[k] = redact(v) if isinstance(v, str) else v

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)


class _SizeRollingFileHandler(RotatingFileHandler):
    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        base = Path(self.baseFilename)

        if base.exists():
            ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            archived = base.with_name(f"{base.stem}_{ts}{base.suffix}")
            base.rename(archived)

            self._cleanup_old_logs(base)

        self.stream = self._open()


class InMemoryLogBuffer(logging.Handler):
    def __init__(self, maxlen: int = 500) -> None:
        super().__init__()
        self._buf: Deque[str] = deque(maxlen=maxlen)
        self._lock = Lock()
        self._fmt = JsonFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self._fmt.format(record)
            with self._lock:
                self._buf.append(line)
        except Exception:
            self.handleError(record)

    def drain(self, since_index: int | None = None) -> tuple[list[str], int]:
        with self._lock:
            buf = list(self._buf)
        total = len(buf)
        if since_index is None or since_index >= total:
            return buf, total
        return buf[since_index:], total

    def resize(self, maxlen: int) -> None:
        with self._lock:
            self._buf = deque(self._buf, maxlen=maxlen)


log_buffer = InMemoryLogBuffer()


def setup_logging(cfg: LogConfig | None = None) -> None:
    if cfg is None:
        cfg = LogConfig()

    root = logging.getLogger()
    root.setLevel(cfg.level)

    handlers: list[logging.Handler] = []

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JsonFormatter())
    handlers.append(console)

    if cfg.file_path:
        base = Path(cfg.file_path)
        log_path = _timestamped_path(cfg.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _cleanup_old_logs(base, cfg.max_files)

        fh = _SizeRollingFileHandler(
            filename=str(log_path),
            maxBytes=cfg.max_bytes,
            backupCount=0,
            encoding="utf-8",
        )

        fh.setFormatter(JsonFormatter())
        handlers.append(fh)

    log_buffer.resize(cfg.tail_buffer_size)
    handlers.append(log_buffer)

    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            try:
                h.close()
            except Exception:
                pass
    root.handlers = handlers

    for name in cfg.noisy_loggers:
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        lg.propagate = False


def _timestamped_path(file_path: str) -> Path:
    base = Path(file_path)
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    return base.with_name(f"{base.stem}_{ts}{base.suffix}")


@contextmanager
def _swallow():
    try:
        yield
    except Exception:
        pass


def _cleanup_old_logs(base: Path, max_files: int) -> None:
    if max_files <= 0:
        return

    files = sorted(
        base.parent.glob(f"{base.stem}_*{base.suffix}"),
        reverse=True,
    )

    for old in files[max_files:]:
        try:
            old.unlink()
        except OSError:
            pass
