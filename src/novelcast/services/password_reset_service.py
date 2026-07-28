# novelcast/services/password_reset_service.py

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from novelcast.auth.password_reset import generate_reset_token
from novelcast.utils.hashing import hash_password

logger = logging.getLogger(__name__)

RESET_FILE_PATH = Path("data") / "password-reset.txt"


class PasswordResetService:
    TOKEN_TTL_HOURS = 1

    def __init__(self, repo, users_repo, auth_service):
        self.repo = repo
        self.users_repo = users_repo
        self.auth_service = auth_service

    def request_reset(self, username: str) -> str | None:
        user = self.users_repo.get_by_username(username)
        if not user:
            return None

        token = generate_reset_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_TTL_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

        self.repo.create_token(user["id"], token, expires_at)

        self._write_reset_file(username, token, expires_at)

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

        self.users_repo.update(record["user_id"], password_hash=hash_password(new_password))
        self.repo.mark_used(token)
        self._clear_reset_file()
        return True

    def _write_reset_file(self, username: str, token: str, expires_at: str) -> None:
        try:
            RESET_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            RESET_FILE_PATH.write_text(
                "NovelCast password reset requested\n"
                "\n"
                f"  Code:    {token}\n"
                f"  User:    {username}\n"
                f"  Expires: {expires_at} UTC\n"
                "\n"
                "Go to /reset-password and paste this code in the 'Reset code' field.\n"
                "This file is overwritten on each new request and cleared once the\n"
                "password is successfully changed.\n"
            )
        except OSError:
            logger.exception("Failed to write password reset file")

    def _clear_reset_file(self) -> None:
        try:
            RESET_FILE_PATH.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to remove password reset file")