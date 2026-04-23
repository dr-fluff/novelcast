class StoriesRepository:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        return self.db.fetchall(
            "SELECT * FROM stories ORDER BY created_at DESC",
            ()
        )

    def get_by_id(self, story_id: int):
        return self.db.fetchone(
            "SELECT * FROM stories WHERE id = ?",
            (story_id,),
        )

    def get_by_url(self, url: str):
        return self.db.fetchone(
            "SELECT * FROM stories WHERE source_url = ?",
            (url,),
        )

    def create(self, title: str, author: str | None, url: str | None):
        return self.db.execute(
            """
            INSERT INTO stories (title, author, source_url)
            VALUES (?, ?, ?)
            """,
            (title, author, url),
        )

    def delete(self, story_id: int):
        return self.db.execute(
            "DELETE FROM stories WHERE id = ?",
            (story_id,),
        )