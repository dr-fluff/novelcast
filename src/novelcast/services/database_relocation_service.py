"""
novelcast/services/database_relocation_service.py

Moves the SQLite database file (and its WAL/SHM sidecars) to a new path,
builds a fresh engine at the new location, and rebinds the shared
SessionLocal sessionmaker to it -- live, with no process restart.

Safety: uses novelcast.db.access_gate to block new repository sessions
and drain in-flight ones before the engine is disposed and swapped, so
no request can open a fresh connection against the old (moved-away) path.
"""

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from novelcast.db.access_gate import db_exclusive_access
from novelcast.db.engine import build_engine

logger = logging.getLogger(__name__)

_ENV_KEY = "DATABASE_URL"
_SIDECAR_SUFFIXES = ("-wal", "-shm")


class DatabaseRelocationError(Exception):
    pass


class DatabaseRelocationService:
    def __init__(
        self,
        engine: Engine,
        session_factory: sessionmaker,
        current_db_path: str,
        env_file: str = ".env",
        on_engine_replaced: Callable[[Engine], None] | None = None,
    ):
        self.engine = engine
        self.session_factory = session_factory
        self.current_db_path = Path(current_db_path)
        self.env_file = Path(env_file)
        self.on_engine_replaced = on_engine_replaced

    def relocate(self, new_db_path: str) -> None:
        """Validate, move the DB file (+ sidecars), rebuild the engine at
        the new path, and rebind SessionLocal to it -- live. Raises
        DatabaseRelocationError on any failure."""
        new_path = Path(new_db_path).expanduser().resolve()
        old_path = self.current_db_path.resolve()

        if new_path == old_path:
            raise DatabaseRelocationError("New path is the same as the current path.")
        if new_path.exists():
            raise DatabaseRelocationError(f"A file already exists at {new_path}.")
        if not old_path.exists():
            raise DatabaseRelocationError(f"Current database file not found at {old_path}.")

        new_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(new_path.parent, os.W_OK):
            raise DatabaseRelocationError(f"Directory not writable: {new_path.parent}")

        try:
            with db_exclusive_access(timeout=30.0):
                self._checkpoint_and_close()
                moved_sidecars = self._move_with_sidecars(old_path, new_path)

                new_url = f"sqlite:///{new_path}"
                try:
                    new_engine = build_engine(new_url)
                except Exception as e:
                    logger.exception("Failed to build engine at new path; rolling back move")
                    self._move_with_sidecars(new_path, old_path, sidecars=moved_sidecars)
                    raise DatabaseRelocationError(
                        "Failed to open database at new path; rolled back."
                    ) from e

                self.session_factory.configure(bind=new_engine)
                self.engine = new_engine
                self.current_db_path = new_path

                try:
                    self._update_env(new_path)
                except Exception as e:
                    # File already moved and the engine is already live at the new
                    # path -- this is now an out-of-sync .env, not a correctness
                    # issue, but the next cold start would read the wrong path.
                    logger.exception(
                        "Database relocated and engine repointed, but failed to update "
                        ".env -- fix DATABASE_URL manually before the next restart"
                    )
                    raise DatabaseRelocationError(
                        "Database moved and is live at the new path, but updating .env "
                        "failed. Update DATABASE_URL manually before the next restart."
                    ) from e

                if self.on_engine_replaced:
                    self.on_engine_replaced(new_engine)
        except RuntimeError as e:
            raise DatabaseRelocationError(str(e)) from e
        except TimeoutError as e:
            raise DatabaseRelocationError(str(e)) from e

        logger.info("Database relocated to %s and is now live -- no restart needed", new_path)

    def _checkpoint_and_close(self) -> None:
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
            conn.commit()
        self.engine.dispose()

    def _move_with_sidecars(self, src: Path, dst: Path, sidecars: list[str] | None = None) -> list[str]:
        shutil.move(str(src), str(dst))

        suffixes = sidecars if sidecars is not None else _SIDECAR_SUFFIXES
        moved = []
        for suffix in suffixes:
            side_src = Path(str(src) + suffix)
            if side_src.exists():
                shutil.move(str(side_src), str(dst) + suffix)
                moved.append(suffix)
        return moved

    def _update_env(self, new_path: Path) -> None:
        new_url = f"sqlite:///{new_path}"

        if self.env_file.exists():
            lines = self.env_file.read_text().splitlines()
        else:
            lines = []

        pattern = re.compile(rf"^{_ENV_KEY}\s*=")
        replaced = False
        for i, line in enumerate(lines):
            if pattern.match(line):
                lines[i] = f"{_ENV_KEY}={new_url}"
                replaced = True
                break

        if not replaced:
            lines.append(f"{_ENV_KEY}={new_url}")

        self.env_file.write_text("\n".join(lines) + "\n")