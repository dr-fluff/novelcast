# novelcast/db/repositories/chapters_repository.py

class ChaptersRepository:
    def __init__(self, db):
        self.db = db

    def upsert(self, story_id: int, chapter_number: int, title: str, url: str):
        return self.db.execute(
            """
            INSERT INTO chapters (story_id, chapter_number, title, url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                chapter_number = excluded.chapter_number,
                title = excluded.title
            """,
            (story_id, chapter_number, title, url),
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