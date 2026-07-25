# novelcast/services/user_service.py

from novelcast.utils.hashing import hash_password


class UserService:
    def __init__(self, repo):
        self.repo = repo

    def get_user(self, username: str):
        return self.repo.get_by_username(username)

    def get_user_by_id(self, user_id: int):
        return self.repo.get_by_id(user_id)

    def create_user(self, username: str, password: str, is_root: bool = False):
        return self.repo.create(username, hash_password(password), int(bool(is_root)))

    def count_users(self):
        return self.repo.count()

    def get_all_users(self):
        return self.repo.list()

    def delete_user(self, user_id: int) -> None:
        self.repo.delete(user_id)

    def promote_to_admin(self, user_id: int):
        return self.repo.set_root(user_id)

    def update_user(
        self,
        user_id: int,
        username: str | None = None,
        password: str | None = None,
        is_root: bool | None = None,
    ):
        if username is not None:
            username = username.strip()
            if not username:
                raise ValueError("Username cannot be empty")

        if password is not None and password == "":
            password = None

        password_hash = hash_password(password) if password is not None else None
        return self.repo.update(
            user_id,
            username=username,
            password_hash=password_hash,
            is_root=is_root,
        )
