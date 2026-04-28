class ProgressRepository:
    def __init__(self, query_manager):
        self.qm = query_manager

    def get_progress(self, user_id: int, story_id: int):
        return self.qm.db.fetchone(self.qm.sql("progress.get_progress"), (user_id, story_id))

    def set_progress(self, user_id: int, story_id: int, last_chapter_id: int, last_position: int):
        return self.qm.db.execute(
            self.qm.sql("progress.set_progress"),
            (user_id, story_id, last_chapter_id, last_position),
        )
