class BaseAdapter:

    def __init__(self, config=None):
        self.config = config or {}

    def get_metadata(self, html: str):
        raise NotImplementedError

    def get_chapter_list(self, url: str):
        raise NotImplementedError

    def get_chapter_content(self, html: str):
        raise NotImplementedError