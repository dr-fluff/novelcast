import hashlib


class UserService:
    def __init__(self, repo):
        self.repo = repo

    def get_user(self, username: str):
        return self.repo.get_by_username(username)

    def get_user_by_id(self, user_id: int):
        return self.repo.get_by_id(user_id)

    def create_user(self, username: str, password: str, is_root: bool = False):
        password_hash = self._hash_password(password)
        return self.repo.create(username, password_hash, int(bool(is_root)))

    def count_users(self):
        return self.repo.count()

    def get_all_users(self):
        return self.repo.list()

    def promote_to_admin(self, user_id: int):
        return self.repo.set_root(user_id)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()