from pathlib import Path


class PageService:
    def __init__(self, stories_repo):
        self.stories_repo = stories_repo

    def get_dashboard(self, sort_key: str):
        stories = self.stories_repo.get_all()

        if sort_key == "title":
            stories.sort(key=lambda x: x["title"].lower())

        return stories

    def get_story(self, url: str):
        return None, None

    def get_chapter(self, url: str, chapter: str):
        return None, None, "Not implemented"