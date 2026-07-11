# novelcast/db/session.py

from sqlalchemy.orm import Session, sessionmaker

from .engine import engine

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # prevents lazy-load errors after commit in FastAPI
)


def get_session():
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
