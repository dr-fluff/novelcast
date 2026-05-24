# novelcast/db/repositories/sync_repository.py


from novelcast.db.repositories.base import BaseRepository

class SyncRepository(BaseRepository):
    def __init__(self, chapters_repo):
        self.chapters = chapters_repo

    def get_missing_chapters(self, story_id: int) -> list[int]:
        online = self.chapters.get_chapter_numbers(story_id)      # set[int]
        downloaded = self.chapters.get_downloaded_numbers(story_id)  # set[int]
        return sorted(online - downloaded)

    def get_latest_numbers(self, story_id: int) -> tuple[int, int]:
        all_numbers = self.chapters.get_chapter_numbers(story_id)
        downloaded = self.chapters.get_downloaded_numbers(story_id)
        latest_online = max(all_numbers) if all_numbers else 0
        latest_downloaded = max(downloaded) if downloaded else 0
        return latest_downloaded, latest_online
