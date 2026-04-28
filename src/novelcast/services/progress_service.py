class ProgressService:
    def __init__(self, repo):
        self.repo = repo

    def get_progress(self, user_id: int, story_id: int):
        return self.repo.get_progress(user_id, story_id)

    def set_progress(self, user_id: int, story_id: int, last_chapter_id: int, last_position: int):
        return self.repo.set_progress(user_id, story_id, last_chapter_id, last_position)
