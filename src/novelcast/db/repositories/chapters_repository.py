# novelcast/db/repositories/chapters_repository.py

class ChaptersRepository:
    def __init__(self, db):
        self.db = db

    def create(self, story_id: int, chapter_number: int, title: str | None, url: str | None, file_path: str | None = None, is_downloaded: int = 0):
        return self.db.execute(
            """
            INSERT INTO chapters (story_id, chapter_number, title, url, file_path, is_downloaded)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (story_id, chapter_number, title, url, file_path, is_downloaded),
        )

    def upsert(self, story_id: int, chapter_number: int, title: str | None, url: str | None, file_path: str | None = None, is_downloaded: int = 0):
        return self.db.execute(
            """
            INSERT INTO chapters (story_id, chapter_number, title, url, file_path, is_downloaded)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                story_id = excluded.story_id,
                chapter_number = excluded.chapter_number,
                title = excluded.title,
                file_path = excluded.file_path,
                is_downloaded = excluded.is_downloaded
            """,
            (story_id, chapter_number, title, url, file_path, is_downloaded),
        )

    def mark_downloaded(self, story_id: int, chapter_number: int, file_path: str):
        return self.db.execute(
            """
            UPDATE chapters
            SET is_downloaded = 1,
                file_path = ?
            WHERE story_id = ? AND chapter_number = ?
            """,
            (file_path, story_id, chapter_number),
        )

    def get_all_numbers(self, story_id: int):
        rows = self.db.fetchall(
            "SELECT chapter_number FROM chapters WHERE story_id = ?",
            (story_id,),
        )
        return {r[0] for r in rows}
    def get_numbers(self, story_id: int):
        return self.get_all_numbers(story_id)
    def list_downloaded_by_story(self, story_id: int):
        return self.db.fetchall(
            "SELECT * FROM chapters WHERE story_id = ? AND is_downloaded = 1 ORDER BY chapter_number",
            (story_id,),
        )

    def get_by_id(self, chapter_id: int):
        return self.db.fetchone(
            "SELECT * FROM chapters WHERE id = ?",
            (chapter_id,),
        )

    def get_ids_by_story(self, story_id: int):
        rows = self.db.fetchall(
            "SELECT id FROM chapters WHERE story_id = ? AND is_downloaded = 1 ORDER BY chapter_number",
            (story_id,),
        )
        return [r["id"] for r in rows]

    def get_downloaded_numbers(self, story_id: int):
        rows = self.db.fetchall(
            """
            SELECT chapter_number
            FROM chapters
            WHERE story_id = ? AND is_downloaded = 1
            """,
            (story_id,),
        )
        return {r[0] for r in rows}

    def get_by_number(self, story_id: int, chapter_number: int):
        return self.db.fetchone(
            """
            SELECT * FROM chapters
            WHERE story_id = ? AND chapter_number = ?
            """,
            (story_id, chapter_number),
        )