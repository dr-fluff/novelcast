# novelcast/services/progress_service.py


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

    def set_progress(self, user_id: int, story_id: int, chapter_id: int, last_position: int) -> None:
        self.repo.set_progress(user_id, story_id, chapter_id, last_position)

    def advance_furthest_chapter(self, user_id: int, story_id: int, chapter_id: int, last_position: int) -> None:
        self.repo.advance_furthest_chapter(user_id, story_id, chapter_id, last_position)
    
    def delete_progress(self, user_id: int, story_id: int) -> None:
        self.repo.delete_progress(user_id, story_id)
