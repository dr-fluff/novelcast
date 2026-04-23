# novelcast/db/repositories/sync_repository.py

class SyncRepository:
    def __init__(self, chapters_repo):
        self.chapters = chapters_repo

    def get_missing_chapters(self, story_id: int):
        online = self.chapters.get_all_numbers(story_id)
        downloaded = self.chapters.get_downloaded_numbers(story_id)

        return sorted(list(online - downloaded))

    def get_latest_numbers(self, story_id: int):
        all_numbers = self.chapters.get_all_numbers(story_id)
        downloaded = self.chapters.get_downloaded_numbers(story_id)

        latest_online = max(all_numbers) if all_numbers else 0
        latest_downloaded = max(downloaded) if downloaded else 0

        return latest_downloaded, latest_online