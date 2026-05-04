# novelcast/services/password_reset_service.py

from datetime import datetime, timedelta, timezone

from novelcast.auth.password_reset import generate_reset_token


class PasswordResetService:
    def __init__(self, repo, users_repo, auth_service):
        self.repo = repo
        self.users_repo = users_repo
        self.auth_service = auth_service

    def request_reset(self, username: str):
        user = self.users_repo.get_user(username)
        if not user:
            return None

        token = generate_reset_token()

        expires_at = (datetime.utcnow() + timedelta(hours=1)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.repo.create_token(user["id"], token, expires_at)

        # TODO: send email instead of returning token
        return token

    def reset_password(self, token: str, new_password: str):
        record = self.repo.get_valid_token(token)
        if not record:
            return False

        if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
            return False
            return False

        user_id = record["user_id"]

        new_hash = self.auth_service._hash_password(new_password)

        self.users_repo.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id),
        )

        self.repo.mark_used(token)
        return True