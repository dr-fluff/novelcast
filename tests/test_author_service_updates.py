from novelcast.services.story_service import StoryService


class DummyStoryRepo:
    def __init__(self):
        self.calls = []


class DummyAuthorRepo:
    def __init__(self):
        self.updated = []
        self.link_calls = []

    def update(self, author_id, name, bio=None, picture_path=None):
        self.updated.append({"author_id": author_id, "name": name, "bio": bio, "picture_path": picture_path})
        return {"id": author_id, "name": name, "bio": bio, "picture_path": picture_path, "links": []}

    def set_links(self, author_id, links):
        self.link_calls.append((author_id, links))
        return links


def test_update_author_passthroughs_cover_and_links():
    author_repo = DummyAuthorRepo()
    service = StoryService(DummyStoryRepo(), author_repo=author_repo)

    result = service.update_author(
        7,
        name="Ada Lovelace",
        bio="Mathematician",
        picture_path="/tmp/ada.jpg",
        links=[{"label": "Site", "url": "https://example.com"}],
    )

    assert result["name"] == "Ada Lovelace"
    assert result["bio"] == "Mathematician"
    assert result["picture_path"] == "/tmp/ada.jpg"
    assert author_repo.updated[0]["author_id"] == 7
    assert author_repo.link_calls == [(7, [{"label": "Site", "url": "https://example.com"}])]
