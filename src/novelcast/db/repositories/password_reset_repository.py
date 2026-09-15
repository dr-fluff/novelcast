# novelcast/db/repositories/password_reset_repository.py

from datetime import datetime

from sqlalchemy import select

from novelcast.db.models.user import PasswordResetToken
from novelcast.db.repositories.base import BaseRepository

TOKEN_ID = "id"
TOKEN_USER_ID = "user_id"
TOKEN_TOKEN = "token"
TOKEN_EXPIRES_AT = "expires_at"
TOKEN_USED = "used"
TOKEN_CREATED_AT = "created_at"


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
        TOKEN_ID: row.id,
        TOKEN_USER_ID: row.user_id,
        TOKEN_TOKEN: row.token,
        TOKEN_EXPIRES_AT: row.expires_at.isoformat(),
        TOKEN_USED: int(row.used),
        TOKEN_CREATED_AT: row.created_at,
    }
