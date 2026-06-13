class ProgressService:
    def __init__(self, repo):
        self.repo = repo

    def get_progress(self, user_id: int, story_id: int):
        return self.repo.get_progress(user_id, story_id)

    def get_all_for_user(self, user_id: int):
        return self.repo.get_all_for_user(user_id)

    def get_chapter_page(self, user_id: int, chapter_id: int) -> dict:
        return self.repo.get_chapter_page(user_id, chapter_id)

    def set_chapter_page(self, user_id: int, chapter_id: int, page: int, anchor: int = 0) -> None:
        self.repo.set_chapter_page(user_id, chapter_id, page, anchor)