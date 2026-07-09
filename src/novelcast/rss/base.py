from abc import ABC, abstractmethod


class BaseRssReader:
    SITE = ""

    def __init__(self, rss_service):
        self.rss_service = rss_service

    def get_story_site_ids(self):
        return self.rss_service.story_service.get_story_site_ids(self.site)

    def build_feed(self):
        raise NotImplementedError

    def fetch(self, url):
        raise NotImplementedError

    def parse(self, text):
        raise NotImplementedError