# novelcast/services/password_reset_service.py

import logging
from datetime import datetime, timedelta, timezone

from novelcast.auth.password_reset import generate_reset_token
from novelcast.utils.hashing import hash_password

logger = logging.getLogger(__name__)


class PasswordResetService:
    TOKEN_TTL_HOURS = 1

    def __init__(self, repo, users_repo, auth_service):
        self.repo = repo
        self.users_repo = users_repo
        self.auth_service = auth_service

    def request_reset(self, username: str) -> str | None:
        user = self.users_repo.get_user(username)
        if not user:
            return None

        token = generate_reset_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_TTL_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

        self.repo.create_token(user["id"], token, expires_at)

        # TODO: replace with email delivery
        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        record = self.repo.get_valid_token(token)
        if not record:
            return False

        expires_at = datetime.fromisoformat(record["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            return False

        self.users_repo.update_password(record["user_id"], hash_password(new_password))
        self.repo.mark_used(token)
        return True
