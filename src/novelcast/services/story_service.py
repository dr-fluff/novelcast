class StoryService:
    def __init__(self, repo):
        self.repo = repo

    def get_all_stories(self):
        return self.repo.get_all()

    def get_story(self, story_id: int):
        return self.repo.get_by_id(story_id)

    def create_story(self, title: str, author: str | None = None, url: str | None = None):
        return self.repo.create(title, author, url)

    def delete_story(self, story_id: int):
        return self.repo.delete(story_id)