# novelcast/db/repositories/password_reset_repository.py

from datetime import datetime

from sqlalchemy import select

from novelcast.db.models.user import PasswordResetToken
from novelcast.db.repositories.base import BaseRepository


class PasswordResetRepository(BaseRepository):
    def create_token(self, user_id: int, token: str, expires_at: str) -> None:
        with self.session() as db:
            db.add(
                PasswordResetToken(
                    user_id=user_id,
                    token=token,
                    expires_at=datetime.fromisoformat(expires_at),
                )
            )

    def get_valid_token(self, token: str) -> dict | None:
        with self.session_no_commit() as db:
            row = db.scalars(
                select(PasswordResetToken).where(
                    PasswordResetToken.token == token,
                    ~PasswordResetToken.used,
                )
            ).first()
            return _token_to_dict(row)

    def mark_used(self, token: str) -> None:
        with self.session() as db:
            row = db.scalars(select(PasswordResetToken).where(PasswordResetToken.token == token)).first()
            if row:
                row.used = True


def _token_to_dict(row: PasswordResetToken | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "token": row.token,
        "expires_at": row.expires_at.isoformat(),
        "used": int(row.used),
        "created_at": row.created_at,
    }
