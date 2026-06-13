import logging
import requests
import xml.etree.ElementTree as ET
from .base import BaseRssReader

logger = logging.getLogger(__name__)


class RoyalRoadRss(BaseRssReader):
    def __init__(self, rss_service):
        self.rss_service = rss_service
        self.base_rss_url = "https://www.royalroad.com/fiction/syndication/"
        self.story_site_ids = set()

    def build_feed(self) -> str:
        ids = self.rss_service.get_royalroad_ids()

        logger.debug("RoyalRoad build_feed | ids=%s", ids)

        if not ids:
            return ""

        return self.base_rss_url + ",".join(sorted(set(ids)))

    def fetch(self, url: str) -> str:
        logger.debug("RoyalRoad fetch | url=%s", url)

        if not url:
            return ""

        try:
            r = requests.get(
                url,
                timeout=10,
                headers={"User-Agent": "NovelCast-RSS/1.0"},
            )
            r.raise_for_status()
            return r.text

        except Exception:
            logger.exception("RoyalRoad RSS fetch failed")
            return ""

    def parse(self, xml_text: str) -> list[dict]:
        logger.debug("RoyalRoad parse called")

        if not xml_text:
            return []

        root = ET.fromstring(xml_text)
        items = []

        for item in root.findall(".//item"):
            items.append({
                "title": item.findtext("title"),
                "link": item.findtext("link"),
                "published": item.findtext("pubDate"),
                "source": "royalroad",
            })

        logger.debug("RoyalRoad parsed items=%d", len(items))
        return items