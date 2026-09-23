"""
novelcast/db/engine.py

Creates the SQLAlchemy engine with SQLite-specific pragmas.
Import `engine` from here everywhere — never create a second one.
build_engine() is exposed for callers (e.g. database relocation) that
need to construct a fresh engine at a different path.
"""

import logging
import re
from pathlib import Path

from sqlalchemy import create_engine, event

from novelcast.core.config import AppConfig

logger = logging.getLogger(__name__)

_SQLITE_URL_RE = re.compile(r"^sqlite:///(.+)$")


def db_path_from_url(database_url: str) -> str:
    """Extract the filesystem path from a `sqlite:///...` URL."""
    match = _SQLITE_URL_RE.match(database_url)
    if not match:
        raise ValueError(f"Unsupported database_url (expected sqlite:///...): {database_url!r}")
    return match.group(1)


def build_engine(database_url: str | None = None):
    if database_url is None:
        database_url = AppConfig().database_url

    db_path = db_path_from_url(database_url)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    new_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(new_engine, "connect")
    def set_pragmas(conn, _record):
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

    logger.info("Engine created", extra={"db_path": db_path})
    return new_engine


engine = build_engine()

