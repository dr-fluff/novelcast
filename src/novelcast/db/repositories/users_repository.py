# novelcast/db/repositories/users_repository.py

"""
Replaces the old UsersRepository that took (db, qm).
Now takes only a session_factory from SessionLocal.

All method signatures are preserved so UserService and AuthService
don't need to change at all.
"""

from sqlalchemy import select, func

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.user import User


class UsersRepository(BaseRepository):

    def get_by_id(self, user_id: int) -> dict | None:
        with self.session_no_commit() as db:
            user = db.get(User, user_id)
            return _to_dict(user)

    def get_by_username(self, username: str) -> dict | None:
        with self.session_no_commit() as db:
            user = db.scalars(
                select(User).where(User.username == username)
            ).first()
            return _to_dict(user)

    def list(self) -> list[dict]:
        with self.session_no_commit() as db:
            users = db.scalars(select(User)).all()
            return [_to_dict(u) for u in users]

    def count(self) -> int:
        with self.session_no_commit() as db:
            return db.scalar(select(func.count()).select_from(User))

    def create(self, username: str, password_hash: str, is_root: int = 0) -> int:
        with self.session() as db:
            user = User(
                username=username,
                password_hash=password_hash,
                is_root=bool(is_root),
            )
            db.add(user)
            db.flush()          # populates user.id before commit
            return user.id

    def set_root(self, user_id: int) -> None:
        with self.session() as db:
            user = db.get(User, user_id)
            if user:
                user.is_root = True

    def delete(self, user_id: int) -> None:
        with self.session() as db:
            user = db.get(User, user_id)
            if user:
                db.delete(user)


# ── helpers ──────────────────────────────────────────────────────────────────

def _to_dict(user: User | None) -> dict | None:
    """
    Convert ORM object → plain dict so services don't import ORM models.
    Preserves the row["field"] access pattern your services already use.
    """
    if user is None:
        return None
    return {
        "id":            user.id,
        "username":      user.username,
        "password_hash": user.password_hash,
        "is_root":       int(user.is_root),
        "created_at":    user.created_at,
    }
