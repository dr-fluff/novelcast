from novelcast.core.context import AppContext

class UserService:
    def __init__(self, qm):
        self.qm = qm

    def create_user(self, username, password_hash, role="user"):
        self.qm.run("users.create_user", (username, password_hash, role))

    def get_user(self, username):
        return self.qm.fetchone("users.get_by_username", (username,))