import logging
import sys
import json
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

request_id_ctx: ContextVar[str] = ContextVar("request_id", default=None)


import re

TOKEN_RE = re.compile(r"bot\d+:[A-Za-z0-9:_-]+")
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*")

def redact(value: str) -> str:
    if not isinstance(value, str):
        return value
    value = TOKEN_RE.sub("bot***:***", value)
    value = BEARER_RE.sub("Bearer ***", value)
    return value



class TimestampRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        base = Path(self.baseFilename)

        rotated = base.with_name(f"{base.stem}_{timestamp}{base.suffix}")

        if base.exists():
            base.rename(rotated)

        self.stream = self._open()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "request_id": request_id_ctx.get(),
        }

        if hasattr(record, "extra_data"):
            safe_extra = {}

            for k, v in record.extra_data.items():
                if isinstance(v, str):
                    safe_extra[k] = redact(v)
                else:
                    safe_extra[k] = v

            log.update(safe_extra)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, ensure_ascii=False)

def setup_logging(config):
    handlers = []

    root = logging.getLogger()
    root.setLevel(config.log_level.upper())

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JsonFormatter())
    handlers.append(console)

    if config.log_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = TimestampRotatingFileHandler(
            filename=str(log_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=0,
            encoding="utf-8",
        )

        file_handler.setFormatter(JsonFormatter())
        handlers.append(file_handler)

    root.handlers = handlers

    # Suppress everything from these loggers except WARNING+
    for noisy_logger in (
        "websockets",
        "websockets.server",
        "websockets.protocol",
        "websockets.client",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.protocols",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.websockets_impl",
        "asyncio",

        # ADD THESE 👇
        "httpx",
        "httpcore",
        "multipart",
        "python_multipart",
        "starlette",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
        logging.getLogger(noisy_logger).propagate = False