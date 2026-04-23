class UserService:
    def __init__(self, repo):
        self.repo = repo

    def get_user(self, username: str):
        return self.repo.get_by_username(username)

    def create_user(self, username: str, password_hash: str):
        return self.repo.create(username, password_hash)