class ChaptersService:
    def __init__(self, db):
        self.db = db

    def list_by_story(self, story_id: int):
        return self.db.fetchall(
            "SELECT * FROM chapters WHERE story_id = ? ORDER BY chapter_number",
            (story_id,),
        )