class StoriesRepository:
    def __init__(self, db):
        self.db = db

    # ---------- basic reads ----------

    def list(self):
        return self.db.fetchall("stories.list")

    def get_by_id(self, story_id: int):
        return self.db.fetchone("stories.get_by_id", (story_id,))

    def get_by_url(self, url: str):
        return self.db.fetchone("stories.get_by_url", (url,))

    # ---------- writes ----------

    def create(self, title: str, author: str | None, url: str | None):
        return self.db.execute(
            "stories.insert",
            (title, author, url),
        )

    def upsert(self, title: str, author: str | None, url: str):
        return self.db.execute(
            "stories.upsert_by_url",
            (title, author, url),
        )

    def update_metadata(self, story_id: int, title: str, author: str | None):
        return self.db.execute(
            "stories.update_metadata",
            (title, author, story_id),
        )

    def update_paths(self, story_id: int, local_path: str, cover_path: str | None = None):
        return self.db.execute(
            "stories.update_paths",
            (local_path, cover_path, story_id),
        )

    def update_chapter_stats(
        self,
        story_id: int,
        total_chapters: int,
        downloaded_chapters: int,
        latest_downloaded_chapter: int | None = None,
        latest_online_chapter: int | None = None,
        online_chapters: int | None = None,
    ):
        return self.db.execute(
            "stories.update_chapter_stats",
            (
                total_chapters,
                downloaded_chapters,
                latest_downloaded_chapter,
                latest_online_chapter,
                online_chapters,
                story_id,
            ),
        )

    # ---------- chapter-related reads ----------

    def get_chapter_file_paths(self, story_id: int):
        rows = self.db.fetchall("stories.get_chapter_file_paths", (story_id,))
        return [r["file_path"] for r in rows if r.get("file_path")]

    def get_chapter_numbers(self, story_id: int):
        rows = self.db.fetchall("stories.get_chapter_numbers", (story_id,))
        return [r["chapter_number"] for r in rows]

    # ---------- deletes ----------

    def delete(self, story_id: int):
        return self.db.execute("stories.delete", (story_id,))

    def delete_with_relations(self, story_id: int):
        with self.db.transaction():
            self.db.execute("stories.delete_reading_progress", (story_id,))
            self.db.execute("stories.delete_permissions", (story_id,))
            self.db.execute("stories.delete_update_jobs", (story_id,))
            self.db.execute("stories.delete_chapters", (story_id,))
            return self.db.execute("stories.delete", (story_id,))