# novelcast/engine/engine_patreon.py
import json
import logging
import os
import re
import tempfile
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)

_USER_AGENT = "Patreon/126.9.0.15 (Android; Android 14; Scale/2.10)"

_POST_FIELDS = (
    "&fields[post]=content,content_json_string,current_user_can_view,"
    "is_paid,min_cents_pledged_to_view,published_at,title,post_type,"
    "patreon_url,url"
    "&fields[campaign]=name,vanity,url"
    "&fields[media]=id,download_url,file_name"
)

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".m4v"}
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


class PatreonEngine:

    ROOT = "https://www.patreon.com"

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
        output_dir: Optional[str] = None,
        story_match: Optional[str] = None,
        include_locked: bool = False,
    ) -> dict:
        logger.info("Starting Patreon fetch for URL: %s", url)

        if output_dir is None:
            output_dir = os.path.join(tempfile.gettempdir(), "novelcast_patreon")
        os.makedirs(output_dir, exist_ok=True)

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

            viewable = list(reversed(viewable))  # oldest first — chronological order

            self._emit_progress(f"Downloading {len(viewable)} posts", progress_callback, 40)
            post_records = self._collect_post_data(viewable, output_dir, progress_callback)

            self._emit_progress("Done!", progress_callback, 100)

            return {
                "title": creator_name,
                "author": creator_name,
                "url": url,
                "file_path": None,
                "format": "patreon",
                "raw": {
                    "campaign_id": campaign_id,
                    "post_records": post_records,
                    "post_count": len(posts),
                    "viewable_count": len(viewable),
                    "locked_count": locked_count,
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
            logger.info("story_match %r isn't valid regex, falling back to literal match: %s", story_match, e)
            pattern = re.compile(re.escape(story_match), re.I)
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

    def _dedupe_attachments(self, attachments: List[Dict]) -> List[Dict]:
        """If a PDF and an EPUB share the same base filename, drop the PDF —
        EPUB is preferred for better structure/formatting."""
        by_stem: Dict[str, List[tuple]] = {}
        for a in attachments:
            filename = a.get("file_name") or ""
            ext = Path(filename).suffix.lower()
            stem = Path(filename).stem.strip().lower()
            by_stem.setdefault(stem, []).append((ext, a))

        result = []
        for stem, items in by_stem.items():
            exts = {ext for ext, _ in items}
            if ".pdf" in exts and ".epub" in exts:
                result.extend(a for ext, a in items if ext != ".pdf")
            else:
                result.extend(a for _, a in items)
        return result

    def _get_raw_post_content(self, post: Dict) -> tuple[str, str]:
        """Returns (raw_content, format). No interpretation — parser handles it."""
        if post.get("content"):
            return post["content"], "html"
        cjs = post.get("content_json_string")
        if cjs:
            return cjs, "tiptap_json"
        return "", "html"

    def _extract_inline_image_urls(self, tiptap_json_str: str) -> List[str]:
        try:
            doc = json.loads(tiptap_json_str)
        except Exception:
            return []
        urls: List[str] = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "image":
                    src = (node.get("attrs") or {}).get("src")
                    if src:
                        urls.append(src)
                for child in node.get("content", []) or []:
                    walk(child)
            elif isinstance(node, list):
                for n in node:
                    walk(n)

        walk(doc)
        return urls

    def _collect_post_data(self, posts: List[Dict], output_dir: str, progress_callback=None) -> List[Dict]:
        """Download everything from each post — text, PDFs, EPUBs, images —
        without interpreting any of it. Videos are skipped entirely. All
        interpretation (chapter splitting, format conversion) is the parser's
        job; only the engine holds the session/cookie needed to download."""
        post_records = []

        for post_idx, post in enumerate(posts):
            try:
                post_id = post.get("id")
                post_title = post.get("title", "Untitled")
                progress = 40 + (post_idx / len(posts)) * 40
                self._emit_progress(f"Downloading: {post_title}", progress_callback, int(progress))

                raw_content, content_format = self._get_raw_post_content(post)

                inline_images: Dict[str, str] = {}
                if content_format == "tiptap_json" and raw_content:
                    for idx, img_url in enumerate(self._extract_inline_image_urls(raw_content)):
                        ext = Path(urlparse(img_url).path).suffix or ".jpg"
                        file_path = os.path.join(output_dir, f"{post_id}_inline_{idx}{ext}")
                        if self._download_file(img_url, file_path):
                            inline_images[img_url] = file_path

                all_attachments = list(post.get("attachments_media", [])) + list(post.get("attachments", []))
                candidates = self._dedupe_attachments(all_attachments)

                files = []
                for attachment in candidates:
                    download_url = attachment.get("download_url")
                    filename = attachment.get("file_name") or "attachment"
                    if not download_url:
                        continue

                    ext = Path(filename).suffix.lower()
                    if ext in _VIDEO_EXTENSIONS:
                        continue

                    if ext == ".pdf":
                        file_type = "pdf"
                    elif ext == ".epub":
                        file_type = "epub"
                    elif ext in _IMAGE_EXTENSIONS:
                        file_type = "image"
                    else:
                        logger.info("Skipping unsupported attachment type %r on post %s", filename, post_id)
                        continue

                    file_path = os.path.join(output_dir, f"{post_id}_{filename}")
                    if self._download_file(download_url, file_path):
                        files.append({"type": file_type, "path": file_path, "filename": filename})

                post_records.append({
                    "post_id": post_id,
                    "title": post_title,
                    "raw_content": raw_content,
                    "content_format": content_format,
                    "inline_images": inline_images,
                    "files": files,
                })

            except Exception as e:
                logger.error("Failed to download post %s: %s", post.get("id"), e)
                continue

        return post_records

    def list_posts_with_access(
        self,
        url: str,
        story_match: Optional[str] = None,
        max_posts: Optional[int] = None,
    ) -> dict:
        """Fetch a creator's posts with per-post lock status, optionally filtered
        by a title regex. Used by the Add Story preview.

        KNOWN LIMITATION: returns one row per post. A post with multiple PDF/EPUB
        attachments will actually produce multiple chapters at download time —
        this preview does not yet reflect that."""
        campaign_id, creator_name = self._resolve_campaign(url)
        posts = self._fetch_all_posts(campaign_id, max_posts=max_posts)

        if story_match:
            posts = self._filter_posts_for_story(posts, story_match)

        posts = list(reversed(posts))

        result_posts = []
        for idx, p in enumerate(posts, start=1):
            result_posts.append({
                "number": idx,
                "title": p.get("title") or f"Post {idx}",
                "locked": not p.get("current_user_can_view", False),
                "published_at": p.get("published_at"),
            })

        return {
            "creator": creator_name,
            "campaign_id": campaign_id,
            "posts": result_posts,
        }

    def _emit_progress(self, message: str, callback=None, value: int = 0):
        if callback:
            callback(message, value)