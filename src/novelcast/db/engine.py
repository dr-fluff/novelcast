"""
novelcast/db/engine.py

Creates the SQLAlchemy engine with SQLite-specific pragmas.
Import `engine` from here everywhere — never create a second one.
"""

import logging
from pathlib import Path

from sqlalchemy import create_engine, event

logger = logging.getLogger(__name__)


def _build_engine(db_path: str = "data/novelcast.db"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def set_pragmas(conn, _record):
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

    logger.info("Engine created", extra={"db_path": db_path})
    return engine


engine = _build_engine()
