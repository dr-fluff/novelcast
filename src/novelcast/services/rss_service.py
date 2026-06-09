class RssService:
    def __init__(self, story_service):
        self.story_service = story_service

    def get_royalroad_ids(self) -> list[str]:
        stories = self.story_service.get_all_stories()

        return [
            s["source_url"].split("/")[-1]
            for s in stories
            if s.get("auto_update")
            and s.get("source_url", "").startswith("https://www.royalroad.com/")
        ]

    def build_royalroad_feed(self) -> str:
        ids = self.get_royalroad_ids()

        if not ids:
            return ""

        return (
            "https://www.royalroad.com/fiction/syndication/"
            + ",".join(set(ids))
        )