import logging
import sys
import json
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

request_id_ctx: ContextVar[str] = ContextVar("request_id", default=None)


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
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }

        if hasattr(record, "extra_data"):
            log.update(record.extra_data)

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
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=0,
            encoding="utf-8",
        )

        file_handler.setFormatter(JsonFormatter())
        handlers.append(file_handler)

    root.handlers = handlers