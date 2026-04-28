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
        if url:
            existing = self.get_by_url(url)
            if existing:
                self.update_metadata(existing["id"], title, author)
                return existing["id"]

        return self.db.execute(
            """
            INSERT OR IGNORE INTO stories (title, author, source_url)
            VALUES (?, ?, ?)
            """,
            (title, author, url),
        )

    def update_metadata(self, story_id: int, title: str, author: str | None):
        return self.db.execute(
            """
            UPDATE stories
            SET title = ?, author = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, author, story_id),
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

    def update_chapter_stats(self, story_id: int, total_chapters: int, downloaded_chapters: int, latest_downloaded_chapter: int | None = None, latest_online_chapter: int | None = None, online_chapters: int | None = None):
        return self.db.execute(
            """
            UPDATE stories
            SET total_chapters = ?, downloaded_chapters = ?, latest_downloaded_chapter = ?, latest_online_chapter = ?, online_chapters = ?
            WHERE id = ?
            """,
            (total_chapters, downloaded_chapters, latest_downloaded_chapter, latest_online_chapter, online_chapters, story_id),
        )

    def delete(self, story_id: int):
        return self.db.execute(
            "DELETE FROM stories WHERE id = ?",
            (story_id,),
        )