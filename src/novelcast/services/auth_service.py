import hashlib
import string


class AuthService:
    def __init__(self, repo):
        self.repo = repo

    def get_user_from_username(self, username: str):
        return self.repo.get_by_username(username)

    def get_user_by_id(self, user_id: int):
        return self.repo.get_by_id(user_id)

    def authenticate(self, username: str, password: str):
        user = self.get_user_from_username(username)
        if not user:
            return None

        stored_hash = user.get("password_hash")
        if stored_hash is None:
            return None

        if self._check_password(password, stored_hash):
            return user
        return None

    def _check_password(self, password: str, password_hash: str) -> bool:
        if self._looks_like_hash(password_hash):
            return self._hash_password(password) == password_hash
        return password == password_hash

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _looks_like_hash(self, value: str) -> bool:
        return len(value) == 64 and all(c in string.hexdigits for c in value)