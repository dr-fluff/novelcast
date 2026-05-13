# ─────────────────────────────────────────────────────────────────────────────
# novelcast/db/repositories/auth_repository.py
#
# AuthRepository is redundant — AuthService already uses UsersRepository.
# Kept as a thin wrapper so nothing breaks if it's referenced elsewhere.
# ─────────────────────────────────────────────────────────────────────────────

class AuthRepository(BaseRepository):

    def get_user_by_username(self, username: str) -> dict | None:
        from sqlalchemy import select
        from novelcast.db.models.user import User
        with self.session_no_commit() as db:
            user = db.scalars(select(User).where(User.username == username)).first()
            if user is None:
                return None
            return {
                "id":            user.id,
                "username":      user.username,
                "password_hash": user.password_hash,
                "is_root":       int(user.is_root),
            }
