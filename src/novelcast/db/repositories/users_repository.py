class UsersRepository:
    def __init__(self, db):
        self.db = db

    def get_by_username(self, username: str):
        return self.db.fetchone(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )

    def get_by_id(self, user_id: int):
        return self.db.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )

    def create(self, username: str, password_hash: str):
        return self.db.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            (username, password_hash),
        )