class AuthRepository:
    def __init__(self, db):
        self.db = db

    def get_user_by_username(self, username: str):
        return self.db.fetchone(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )