# novelcast/db/repositories/base.py

"""
Base class for all repositories.

Repos receive the SessionLocal factory at construction time.
Each public method opens a session, does its work, commits, and closes.
This is intentionally simple — no Unit of Work, no shared transactions.
If you need multi-repo transactions later, pass a session in explicitly.

Usage:
    class StoriesRepository(BaseRepository):
        def get_by_id(self, story_id: int):
            with self.session() as db:
                return db.get(Story, story_id)
"""

from contextlib import contextmanager
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    @contextmanager
    def session(self):
        """
        Context manager that yields a session and handles
        commit / rollback / close automatically.

            with self.session() as db:
                db.add(thing)
                # commits on exit, rolls back on exception
        """
        db: Session = self._session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def session_no_commit(self):
        """
        Use when you only need to read — skips the commit overhead.
        """
        db: Session = self._session_factory()
        try:
            yield db
        finally:
            db.close()
