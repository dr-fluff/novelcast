from novelcast.core.context import AppContext

class AuthService:
    def __init__(self, qm):
        self.qm = qm

    def get_user_from_username(self, username: str):
        return self.qm.fetchone(
            "users.get_by_username",
            (username,)
        )