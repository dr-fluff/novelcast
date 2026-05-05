# novelcast/db/repositories/chapters_repository.py

class ChaptersRepository:
    def __init__(self, db):
        self.db = db

    def create(self, story_id, chapter_number, title, url, file_path=None, is_downloaded=0):
        return self.db.execute(
            "chapters.insert",
            (story_id, chapter_number, title, url, file_path, is_downloaded),
        )

    def upsert(self, story_id, chapter_number, title, url, file_path=None, is_downloaded=0):
        return self.db.execute(
            "chapters.upsert_by_url",
            (story_id, chapter_number, title, url, file_path, is_downloaded),
        )

    def mark_downloaded(self, story_id, chapter_number, file_path):
        return self.db.execute(
            "chapters.mark_downloaded_by_number",
            (file_path, story_id, chapter_number),
        )

    def get_by_story(self, story_id):
        return self.db.fetchall("chapters.get_by_story", (story_id,))

    def get_by_number(self, story_id, chapter_number):
        return self.db.fetchone(
            "chapters.get_by_number",
            (story_id, chapter_number),
        )

    def get_by_id(self, chapter_id):
        return self.db.fetchone("chapters.get_by_id", (chapter_id,))

    def get_downloaded(self, story_id):
        return self.db.fetchall("chapters.get_downloaded_by_story", (story_id,))

    def get_downloaded_ids(self, story_id):
        rows = self.db.fetchall("chapters.get_ids_downloaded_by_story", (story_id,))
        return [r["id"] for r in rows]

    def get_chapter_numbers(self, story_id):
        rows = self.db.fetchall("chapters.get_numbers_by_story", (story_id,))
        return {r["chapter_number"] for r in rows}