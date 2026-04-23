# novelcast/db/repositories/stories_repository.py

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

    def create(self, title: str, author: str | None, url: str | None, local_path: str | None = None):
        return self.db.execute(
            """
            INSERT INTO stories (title, author, source_url, local_path)
            VALUES (?, ?, ?, ?)
            """,
            (title, author, url, local_path),
        )

    def update_paths(self, story_id: int, local_path: str, cover_path: str | None = None):
        return self.db.execute(
            """
            UPDATE stories
            SET local_path = ?, cover_path = ?
            WHERE id = ?
            """,
            (local_path, cover_path, story_id),
        )

    def update_sync_state(
        self,
        story_id: int,
        downloaded: int,
        online: int,
        latest_downloaded: int,
        latest_online: int
    ):
        return self.db.execute(
            """
            UPDATE stories
            SET
                downloaded_chapters = ?,
                online_chapters = ?,
                latest_downloaded_chapter = ?,
                latest_online_chapter = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (downloaded, online, latest_downloaded, latest_online, story_id),
        )

    def delete(self, story_id: int):
        return self.db.execute(
            "DELETE FROM stories WHERE id = ?",
            (story_id,),
        )