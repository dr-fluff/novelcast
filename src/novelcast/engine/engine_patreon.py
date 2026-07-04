# novelcast/engine/engine_patreon.py
import logging
import os
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Optional, Dict, List, Any
from html.parser import HTMLParser

import requests
import PyPDF2

logger = logging.getLogger(__name__)

_USER_AGENT = "Patreon/126.9.0.15 (Android; Android 14; Scale/2.10)"

_POST_FIELDS = (
    "&fields[post]=content,content_json_string,current_user_can_view,"
    "is_paid,min_cents_pledged_to_view,published_at,title,post_type,"
    "patreon_url,url"
    "&fields[campaign]=name,vanity,url"
    "&fields[media]=id,download_url,file_name"
)

class PatreonEngine:

    ROOT = "https://www.patreon.com"

    CHAPTER_PATTERNS = [
        r"^[Cc]hapter\s+(\d+)(?:\s*:\s*(.+))?$",
        r"^[Cc]hapter\s+(\d+)\s*[-–—]\s*(.+)$",
        r"^(\d+)[.\)]\s+(.+)$",
        r"^[Pp]art\s+(\d+)(?:\s*:\s*(.+))?$",
    ]

    def __init__(self, settings_repo, settings_service):
        self.settings_repo = settings_repo
        self.settings_service = settings_service
        self.session = requests.Session()

    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in {"patreon.com", "www.patreon.com"} if hostname else False

    def _cookie(self) -> str:
        cookie = self.settings_service.get_secret("patreon.session_cookie")
        if not cookie:
            raise ValueError(
                "No Patreon session cookie configured — copy 'session_id' "
                "from your logged-in browser session into settings."
            )
        return cookie

    def _headers(self) -> dict:
        return {
            "User-Agent": _USER_AGENT,
            "Cookie": f"session_id={self._cookie()}",
        }

    def validate_settings(self, test_oauth: bool = False) -> tuple[bool, Optional[str]]:
        try:
            self._cookie()
        except ValueError as e:
            return False, str(e)

        if test_oauth:
            try:
                resp = self.session.get(
                    f"{self.ROOT}/home",
                    headers=self._headers(),
                    timeout=10.0,
                    allow_redirects=True,
                )
                if "/login" in resp.url:
                    return False, "Session cookie is expired or invalid — log into patreon.com again and re-copy 'session_id'."
                resp.raise_for_status()
            except requests.RequestException as e:
                return False, f"Connection error: {e}"

        return True, None

    def fetch(
        self,
        url: str,
        progress_callback=None,
        output_dir="/temp",
        story_match: Optional[str] = None,
        include_locked: bool = False,
    ) -> dict:
        logger.info("Starting Patreon fetch for URL: %s", url)
        logger.debug(
            "Options: story_match=%r include_locked=%s output_dir=%s",
            story_match,
            include_locked,
            output_dir,
        )
        try:
            self._emit_progress("Resolving creator", progress_callback, 5)
            campaign_id, creator_name = self._resolve_campaign(url)

            self._emit_progress(f"Fetching posts from {creator_name}", progress_callback, 20)
            posts = self._fetch_all_posts(campaign_id)

            viewable = [p for p in posts if p.get("current_user_can_view", True)]
            locked_count = len(posts) - len(viewable)

            if story_match:
                viewable = self._filter_posts_for_story(viewable, story_match)
                if not viewable:
                    raise ValueError(f"No accessible posts matched story pattern: {story_match!r}")

            self._emit_progress(f"Processing {len(viewable)} posts", progress_callback, 40)
            chapters = self._extract_chapters_from_posts(viewable, output_dir, progress_callback)

            self._emit_progress("Organizing chapters", progress_callback, 80)
            chapters = self._normalize_chapters(chapters)

            self._emit_progress("Done!", progress_callback, 100)

            return {
                "title": creator_name,
                "author": creator_name,
                "url": url,
                "chapters": [ch["number"] for ch in chapters],
                "file_path": None,
                "format": "patreon",
                "raw": {
                    "campaign_id": campaign_id,
                    "chapters": chapters,
                    "post_count": len(posts),
                    "viewable_count": len(viewable),
                    "locked_count": locked_count,
                    "chapter_count": len(chapters),
                }
            }

        except Exception as e:
            logger.error("Patreon fetch failed: %s", e)
            raise RuntimeError(f"Failed to fetch from Patreon: {e}")

    def check_access(self, url: str) -> dict:
        campaign_id, creator_name = self._resolve_campaign(url)
        posts = self._fetch_all_posts(campaign_id, max_posts=25)

        viewable = sum(1 for p in posts if p.get("current_user_can_view", True))

        return {
            "creator": creator_name,
            "campaign_id": campaign_id,
            "checked": len(posts),
            "viewable": viewable,
            "has_access": viewable > 0,
            "fully_subscribed": viewable == len(posts) if posts else False,
        }

    def check_updates(self, url: str, story_match: Optional[str] = None) -> dict:
        campaign_id, creator_name = self._resolve_campaign(url)
        posts = self._fetch_all_posts(campaign_id, max_posts=5)
        posts = [p for p in posts if p.get("current_user_can_view", True)]

        if story_match:
            posts = self._filter_posts_for_story(posts, story_match)

        return {
            "title": creator_name,
            "author": creator_name,
            "url": url,
            "raw": {
                "campaign_id": campaign_id,
                "latest_posts": [
                    {"title": p.get("title"), "published_at": p.get("published_at")}
                    for p in posts
                ]
            }
        }

    def _extract_creator_from_url(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in {"patreon.com", "www.patreon.com"}:
            return None

        query = parse_qs(parsed.query)
        vanity = (query.get("vanity") or [None])[0]
        if vanity:
            return vanity.strip()

        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return None
        if parts[0].lower() in ("c", "cw") and len(parts) > 1:
            return parts[1]
        return parts[0]

    def _resolve_campaign(self, url: str) -> tuple[str, str]:
        
        logger.info("Resolving creator from URL: %s", url)

        creator = self._extract_creator_from_url(url)
        logger.debug("Extracted creator: %s", creator)
        if not creator:
            raise ValueError(f"Could not parse a Patreon creator from URL: {url}")

        try:
            resp = self.session.get(
                f"{self.ROOT}/{creator}",
                headers=self._headers(),
                timeout=15.0,
                allow_redirects=True,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to load creator page for '{creator}': {e}")

        campaign_id = self._extract_campaign_id(resp.text)
        if not campaign_id:
            raise RuntimeError(
                f"Could not find a campaign ID on {creator}'s page. Patreon "
                f"may have changed their page structure, or the cookie is invalid."
            )

        return campaign_id, creator

    def _extract_campaign_id(self, page: str) -> Optional[str]:
        """Best-effort extraction across the page-structure variants Patreon
        has used. Fragile by nature — this is undocumented, scraped state,
        and Patreon can change it without notice."""
        patterns = [
            r'"campaign":\{"data":\{"id":"(\d+)"',
            r'\\"campaign\\":\{\\"data\\":\{\\"id\\":\\"(\d+)\\"',
        ]
        for pattern in patterns:
            match = re.search(pattern, page)
            if match:
                return match.group(1)
        return None

    def _build_posts_url(self, campaign_id: str, cursor: Optional[str] = None) -> str:
        url = (
            f"{self.ROOT}/api/posts"
            "?include=campaign,attachments,attachments_media"
            f"{_POST_FIELDS}"
            f"&filter[campaign_id]={campaign_id}"
            "&filter[contains_exclusive_posts]=true"
            "&filter[is_draft]=false"
            "&sort=-published_at"
            "&json-api-version=1.0"
        )
        if cursor:
            url += f"&page[cursor]={cursor}"
        return url

    def _fetch_all_posts(self, campaign_id: str, max_posts: Optional[int] = None) -> List[Dict]:
        posts = []
        url = self._build_posts_url(campaign_id)

        while url:
            try:
                resp = self.session.get(url, headers=self._headers(), timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                raise RuntimeError(f"Failed to fetch posts: {e}")

            included = self._transform_included(data.get("included", []))

            for raw_post in data.get("data", []):
                posts.append(self._flatten_post(raw_post, included))
                if max_posts and len(posts) >= max_posts:
                    return posts

            url = data.get("links", {}).get("next")

        logger.info("Fetched %d posts", len(posts))
        return posts

    def _transform_included(self, included: List[Dict]) -> Dict[str, Dict]:
        result: Dict[str, Dict] = {}
        for item in included:
            result.setdefault(item["type"], {})[item["id"]] = item.get("attributes", {})
        return result

    def _flatten_post(self, raw_post: Dict, included: Dict[str, Dict]) -> Dict:
        attrs = dict(raw_post.get("attributes", {}))
        attrs["id"] = raw_post.get("id")

        relationships = raw_post.get("relationships", {})
        attrs["attachments"] = self._resolve_relationship(relationships, included, "attachments")
        attrs["attachments_media"] = self._resolve_relationship(relationships, included, "attachments_media")

        return attrs

    def _resolve_relationship(self, relationships: Dict, included: Dict[str, Dict], key: str) -> List[Dict]:
        rel = relationships.get(key)
        if not rel or not rel.get("data"):
            return []
        out = []
        for ref in rel["data"]:
            attrs = included.get(ref["type"], {}).get(ref["id"])
            if attrs:
                out.append(attrs)
        return out

    def _filter_posts_for_story(self, posts: List[Dict], story_match: str) -> List[Dict]:
        try:
            pattern = re.compile(story_match, re.I)
        except re.error as e:
            raise ValueError(f"Invalid story_match regex {story_match!r}: {e}")
        return [p for p in posts if pattern.search(p.get("title", ""))]

    def _download_file(self, url: str, output_path: str) -> bool:
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=30, allow_redirects=True)
            resp.raise_for_status()
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except Exception as e:
            logger.error("Failed to download file: %s", e)
            return False

    def _extract_chapters_from_posts(self, posts: List[Dict], output_dir: str, progress_callback=None) -> List[Dict]:
        chapters = []

        for post_idx, post in enumerate(posts):
            try:
                post_id = post.get("id")
                post_title = post.get("title", "Untitled")
                progress = 40 + (post_idx / len(posts)) * 40
                self._emit_progress(f"Processing: {post_title}", progress_callback, int(progress))

                text_content = self._extract_post_text(post)
                if text_content:
                    chapters.extend(self._parse_text_post(text_content, post_title))

                for attachment in post.get("attachments_media", []):
                    download_url = attachment.get("download_url")
                    filename = attachment.get("file_name", "attachment")
                    if download_url and filename.lower().endswith(".pdf"):
                        file_path = os.path.join(output_dir, f"{post_id}_{filename}")
                        if self._download_file(download_url, file_path):
                            chapters.extend(self._parse_pdf_file(file_path))

            except Exception as e:
                logger.error("Failed to process post %s: %s", post.get("id"), e)
                continue

        return chapters

    def _extract_post_text(self, post: Dict) -> str:
        """
        KEEP RAW HTML — DO NOT STRIP IT
        """

        if post.get("content"):
            return post["content"]

        cjs = post.get("content_json_string")
        if cjs:
            try:
                import json
                doc = json.loads(cjs)
                return self._tiptap_to_html(doc)  # NOT text
            except Exception as e:
                logger.warning("Failed to parse content_json_string: %s", e)

        return ""

    def _tiptap_to_html(self, node) -> str:
        if isinstance(node, dict):
            if node.get("type") == "text":
                return node.get("text", "")

            inner = "".join(self._tiptap_to_html(c) for c in node.get("content", []) or [])

            if node.get("type") == "paragraph":
                return f"<p>{inner}</p>"
            if node.get("type") == "heading":
                return f"<h3>{inner}</h3>"

            return inner

        if isinstance(node, list):
            return "".join(self._tiptap_to_html(n) for n in node)

        return ""

    def _parse_text_post(self, content: str, post_title: str) -> List[Dict]:

        content = content.strip()
        if not content:
            return []

        lines = content.split("\n")
        chapter_matches = self._find_chapter_headers(lines)

        if chapter_matches:
            return self._split_by_headers(lines, chapter_matches)
        else:
            chapter_num = self._extract_chapter_number_from_title(post_title)
            return [{"number": chapter_num, "title": post_title, "content": content}]

    def _parse_pdf_file(self, file_path: str) -> List[Dict]:
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "rb") as f:
                pdf = PyPDF2.PdfReader(f)
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"

                lines = full_text.split("\n")
                chapter_matches = self._find_chapter_headers(lines)
                if chapter_matches:
                    return self._split_by_headers(lines, chapter_matches)
                return [{"number": 1, "title": Path(file_path).stem, "content": full_text.strip()}]
        except Exception as e:
            logger.error("Failed to parse PDF %s: %s", file_path, e)
            return []

    def _find_chapter_headers(self, lines: List[str]) -> List[tuple]:
        matches = []
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) > 200:
                continue
            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    chapter_num = int(match.group(1))
                    title = match.group(2).strip() if match.lastindex >= 2 else None
                    matches.append((idx, chapter_num, title))
                    break
        return matches

    def _split_by_headers(self, lines: List[str], matches: List[tuple]) -> List[Dict]:
        chapters = []
        for i, (idx, chapter_num, title) in enumerate(matches):
            start = idx + 1
            end = matches[i + 1][0] if i + 1 < len(matches) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            if content:
                chapters.append({"number": chapter_num, "title": title or f"Chapter {chapter_num}", "content": content})
        return chapters

    def _extract_chapter_number_from_title(self, title: str) -> int:
        match = re.search(r"\b(\d+)\b", title)
        return int(match.group(1)) if match else 1

    def _normalize_chapters(self, chapters: List[Dict]) -> List[Dict]:
        chapters.sort(key=lambda x: x.get("number", 0))
        for idx, ch in enumerate(chapters, 1):
            ch["number"] = idx
        return chapters

    def _emit_progress(self, message: str, callback=None, value: int = 0):
        if callback:
            callback(message, value)