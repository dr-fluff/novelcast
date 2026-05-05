class UsersRepository:
    def __init__(self, db):
        self.db = db

    # ---------- internal mapping ----------

    def _map(self, row):
        return row  # no domain logic here

    # ---------- reads ----------

    def get_by_username(self, username: str):
        row = self.db.fetchone("users.get_by_username", (username,))
        return self._map(row)

    def get_by_id(self, user_id: int):
        row = self.db.fetchone("users.get_by_id", (user_id,))
        return self._map(row)

    def list(self):
        rows = self.db.fetchall("users.list")
        return [self._map(r) for r in rows]

    def count(self):
        row = self.db.fetchone("users.count")
        return row["total"] if row else 0

    # ---------- writes ----------

    def create(self, username: str, password_hash: str, is_root: int = 0):
        return self.db.execute(
            "users.create",
            (username, password_hash, is_root),
        )

    def set_root(self, user_id: int):
        return self.db.execute(
            "users.set_root",
            (user_id,),
        )

    def delete(self, user_id: int):
        return self.db.execute("users.delete", (user_id,))