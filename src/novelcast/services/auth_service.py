# novelcast/services/auth_service.py

from novelcast.utils.hashing import verify_password


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

        if verify_password(password, stored_hash):
            return user
        return None
