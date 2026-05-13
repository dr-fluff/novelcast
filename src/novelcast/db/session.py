"""
novelcast/db/session.py

Session factory and FastAPI dependency.

Usage in routes:
    from novelcast.db.session import get_session
    from sqlalchemy.orm import Session

    @router.get("/stories")
    def list_stories(db: Session = Depends(get_session)):
        ...

Usage in scripts / background tasks:
    from novelcast.db.session import SessionLocal
    with SessionLocal() as db:
        ...
"""

from sqlalchemy.orm import sessionmaker, Session

from .engine import engine


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # prevents lazy-load errors after commit in FastAPI
)


def get_session():
    """FastAPI dependency — yields a session, commits on success, rolls back on error."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
