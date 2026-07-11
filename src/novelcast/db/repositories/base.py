# novelcast/db/repositories/base.py

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
