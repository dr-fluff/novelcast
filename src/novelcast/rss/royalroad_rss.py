import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)


class RoyalRoadRss:
    site = "royalroad"

    def __init__(self, rss_service):
        self.rss_service = rss_service

        self.base_rss_url = "https://www.royalroad.com/fiction/syndication/"

    # ------------------------------------------------------------------

    def get_feed_urls(self) -> list[tuple[str, str]]:
        stories = self.rss_service.get_auto_update_stories_by_site(self.site)

        ids = sorted({str(story["story_site_id"]) for story in stories if story.get("story_site_id")})

        if not ids:
            logger.debug("No RoyalRoad stories configured")
            return []

        return [(story_id, f"{self.base_rss_url}{story_id}") for story_id in ids]

    # ------------------------------------------------------------------

    def fetch(self, url: str) -> str:
        logger.debug(
            "RoyalRoad fetch | url=%s",
            url,
        )

        if not url:
            return ""

        try:
            r = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "NovelCast-RSS/1.0",
                },
            )

            logger.debug(
                "RoyalRoad response status=%s content-type=%s length=%s",
                r.status_code,
                r.headers.get("content-type"),
                len(r.content),
            )

            r.raise_for_status()

            return r.content.decode("utf-8-sig")

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None

            if status == 429:
                retry_after = e.response.headers.get("Retry-After") if e.response is not None else None
                logger.warning(
                    "RoyalRoad rate-limited (429) | url=%s retry_after=%s",
                    url,
                    retry_after,
                )
            else:
                logger.exception("RoyalRoad RSS fetch failed")
            return ""

        except Exception:
            logger.exception("RoyalRoad RSS fetch failed")
            return ""

    # ------------------------------------------------------------------

    def parse(self, xml_text: str, story_site_id: str) -> list[dict]:
        logger.debug(
            "RoyalRoad parse called | story_site_id=%s",
            story_site_id,
        )

        if not xml_text:
            return []

        # Remove UTF-8 BOM and whitespace
        xml_text = xml_text.lstrip("\ufeff\r\n\t ")

        try:
            root = ET.fromstring(xml_text)

        except ET.ParseError:
            logger.exception(
                "RoyalRoad XML parse failed. Start=%r",
                xml_text[:200],
            )
            return []

        items = []

        for item in root.findall(".//item"):
            link = item.findtext("link")

            published_raw = item.findtext("pubDate")

            published = None

            if published_raw:
                try:
                    published = parsedate_to_datetime(published_raw)

                except Exception:
                    logger.warning(
                        "Failed parsing RSS date: %s",
                        published_raw,
                    )

            entry = {
                "guid": link,
                "title": item.findtext("title"),
                "link": link,
                "published": published,
                "source": self.site,
                "story_site_id": story_site_id,
            }

            items.append(entry)

        logger.debug(
            "RoyalRoad parsed items=%d for story_site_id=%s",
            len(items),
            story_site_id,
        )

        return items
