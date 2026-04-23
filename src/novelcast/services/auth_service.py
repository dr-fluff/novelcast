class AuthService:
    def __init__(self, repo):
        self.repo = repo

    def get_user_from_username(self, username: str):
        return self.repo.get_user_by_username(username)