# novelcast/db/repositories/password_reset_repository.py


class PasswordResetRepository:
    def __init__(self, db):
        self.db = db

    def create_token(self, user_id: int, token: str, expires_at: str):
        return self.db.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token, expires_at),
        )

    def get_valid_token(self, token: str):
        return self.db.fetchone(
            """
            SELECT * FROM password_reset_tokens
            WHERE token = ? AND used = 0
            """,
            (token,),
        )

    def mark_used(self, token: str):
        return self.db.execute(
            """
            UPDATE password_reset_tokens
            SET used = 1
            WHERE token = ?
            """,
            (token,),
        )