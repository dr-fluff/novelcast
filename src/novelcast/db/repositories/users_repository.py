class UsersRepository:
    def __init__(self, db):
        self.db = db

    def _normalize_user(self, row):
        if not row:
            return None
        row["role"] = "admin" if row.get("is_root") else "user"
        return row

    def get_by_username(self, username: str):
        row = self.db.fetchone(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        )
        return self._normalize_user(row)

    def get_by_id(self, user_id: int):
        row = self.db.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )
        return self._normalize_user(row)

    def list(self):
        rows = self.db.fetchall(
            "SELECT * FROM users",
            (),
        )
        return [self._normalize_user(row) for row in rows]

    def count(self):
        row = self.db.fetchone(
            "SELECT COUNT(*) as total FROM users",
            (),
        )
        return row["total"] if row else 0

    def create(self, username: str, password_hash: str, is_root: int = 0):
        return self.db.execute(
            """
            INSERT INTO users (username, password_hash, is_root)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, is_root),
        )

    def set_root(self, user_id: int):
        return self.db.execute(
            "UPDATE users SET is_root = 1 WHERE id = ?",
            (user_id,),
        )
