# novelcast/engine/engine_patreon.py
import logging
import os
import re
import configparser
import requests
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional, Dict, List, Any
from html.parser import HTMLParser
import PyPDF2

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extract clean text from HTML"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
    
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_script = True
    
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script = False
    
    def handle_data(self, data):
        if not self.in_script:
            self.text_parts.append(data)
    
    def get_text(self):
        return "".join(self.text_parts).strip()


class PatreonEngine:
    """Download stories from Patreon creator posts - matches FanFicFare architecture"""
    
    API_URL = "https://www.patreon.com/api/v2"
    
    CHAPTER_PATTERNS = [
        r"^[Cc]hapter\s+(\d+)(?:\s*:\s*(.+))?$",
        r"^[Cc]hapter\s+(\d+)\s*[-–—]\s*(.+)$",
        r"^(\d+)[.\)]\s+(.+)$",
        r"^[Pp]art\s+(\d+)(?:\s*:\s*(.+))?$",
    ]
    
    def __init__(self, settings_repo, config_service):
        self.settings_repo = settings_repo
        self.config_service = config_service
        self.session = requests.Session()
    
    # -------------------------
    # ROUTING
    # -------------------------
    def can_handle(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        return hostname in {"patreon.com", "www.patreon.com"} if hostname else False
    
    # -------------------------
    # PUBLIC API (matches FanFicFare)
    # -------------------------
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        """
        Fetch posts from Patreon creator and extract chapters.
        
        Returns dict matching FanFicFareEngine format:
        {
            "title": str,
            "author": str,
            "url": str,
            "chapters": list[int],  # Chapter numbers only (for EPUB path case)
            "file_path": str | None,  # Path to EPUB if generated
            "format": str,  # "epub" or "chapters"
            "raw": dict  # Full chapter data with content
        }
        """
        try:
            # Read credentials from INI
            email, password = self._read_config()
            if not email or not password:
                raise ValueError("Email and password required in config")
            
            self._emit_progress("Authenticating with Patreon", progress_callback, 5)
            
            # Authenticate
            access_token = self._authenticate(email, password)
            
            self._emit_progress("Fetching user info", progress_callback, 10)
            
            # Get creator info
            creator_name, campaign_id = self._find_campaign(access_token, url)
            
            self._emit_progress(f"Fetching posts from {creator_name}", progress_callback, 20)
            
            # Fetch all posts
            posts = self._fetch_all_posts(access_token, campaign_id)
            
            self._emit_progress(f"Processing {len(posts)} posts", progress_callback, 40)
            
            # Extract chapters
            chapters = self._extract_chapters_from_posts(
                access_token,
                posts,
                output_dir,
                progress_callback
            )
            
            self._emit_progress("Organizing chapters", progress_callback, 80)
            chapters = self._normalize_chapters(chapters)
            
            self._emit_progress("Done!", progress_callback, 100)
            
            # Return in FanFicFare format
            return {
                "title": creator_name,
                "author": creator_name,
                "url": url,
                "chapters": [ch["number"] for ch in chapters],  # Just numbers
                "file_path": None,  # Patreon doesn't generate EPUB automatically
                "format": "chapters",  # Chapters with content in raw
                "raw": {
                    "campaign_id": campaign_id,
                    "chapters": chapters,  # Full chapter data with content
                    "post_count": len(posts),
                    "chapter_count": len(chapters),
                }
            }
        
        except Exception as e:
            logger.error("Patreon fetch failed: %s", e)
            raise RuntimeError(f"Failed to fetch from Patreon: {e}")
    
    def check_updates(self, url: str) -> dict:
        """Check for new posts - optional, matches FanFicFare interface"""
        try:
            email, password = self._read_config()
            access_token = self._authenticate(email, password)
            creator_name, campaign_id = self._find_campaign(access_token, url)
            
            posts = self._fetch_all_posts(access_token, campaign_id)
            
            return {
                "title": creator_name,
                "author": creator_name,
                "url": url,
                "raw": {
                    "campaign_id": campaign_id,
                    "post_count": len(posts),
                    "latest_posts": [
                        {
                            "title": p.get("attributes", {}).get("title"),
                            "published_at": p.get("attributes", {}).get("published_at"),
                        }
                        for p in posts[:5]
                    ]
                }
            }
        
        except Exception as e:
            logger.error("Update check failed: %s", e)
            raise RuntimeError(f"Failed to check updates: {e}")
    
    # -------------------------
    # CONFIG & AUTH
    # -------------------------
    def _read_config(self) -> tuple:
        """Read email and password from patreon.ini"""
        config_path = "config/patreon.ini"
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        email = config.get("defaults", "email", fallback="").strip()
        password = config.get("defaults", "password", fallback="").strip()
        
        logger.info("Loaded Patreon config from %s", config_path)
        
        return email, password
    
    def _authenticate(self, email: str, password: str) -> str:
        """Authenticate with Patreon and return access token"""
        try:
            response = requests.post(
                "https://www.patreon.com/api/oauth2/token",
                data={
                    "grant_type": "password",
                    "username": email,
                    "password": password,
                    "client_id": "7347-6ba3b1f-secret",
                    "scope": "identity campaigns pledges-to-me",
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise ValueError("No access token in response")
            
            logger.info("Successfully authenticated with Patreon")
            return access_token
        
        except requests.RequestException as e:
            logger.error("Patreon authentication failed: %s", e)
            raise RuntimeError(f"Failed to authenticate: {e}")
    
    # -------------------------
    # API CALLS
    # -------------------------
    def _find_campaign(self, access_token: str, url: str) -> tuple:
        """Find campaign from user's memberships"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.get(
                f"{self.API_URL}/identity?include=memberships.campaign",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            included = data.get("included", [])
            for item in included:
                if item.get("type") == "campaign":
                    campaign_id = item.get("id")
                    campaign_name = item.get("attributes", {}).get("name", "")
                    
                    if campaign_id:
                        logger.info("Found campaign: %s", campaign_name)
                        return campaign_name, campaign_id
            
            raise ValueError("No campaigns found in memberships")
        
        except requests.RequestException as e:
            logger.error("Failed to find campaign: %s", e)
            raise RuntimeError(f"Failed to find campaign: {e}")
    
    def _fetch_all_posts(self, access_token: str, campaign_id: str) -> List[Dict]:
        """Fetch all posts from campaign with pagination"""
        headers = {"Authorization": f"Bearer {access_token}"}
        posts = []
        cursor = None
        
        while True:
            params = {
                "include": "attachments",
                "fields[post]": "title,content,published_at,post_type",
                "sort": "-published_at",
                "page[count]": 100,
            }
            if cursor:
                params["page[cursor]"] = cursor
            
            try:
                response = requests.get(
                    f"{self.API_URL}/campaigns/{campaign_id}/posts",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                posts.extend(data.get("data", []))
                
                cursor = data.get("meta", {}).get("pagination", {}).get("cursors", {}).get("next")
                if not cursor:
                    break
            
            except requests.RequestException as e:
                logger.error("Failed to fetch posts: %s", e)
                raise RuntimeError(f"Failed to fetch posts: {e}")
        
        logger.info("Fetched %d posts", len(posts))
        return posts
    
    def _download_file(self, url: str, output_path: str) -> bool:
        """Download a file"""
        try:
            response = requests.get(url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            logger.info("Downloaded file to %s", output_path)
            return True
        except Exception as e:
            logger.error("Failed to download file: %s", e)
            return False
    
    # -------------------------
    # CHAPTER EXTRACTION
    # -------------------------
    def _extract_chapters_from_posts(
        self,
        access_token: str,
        posts: List[Dict],
        output_dir: str,
        progress_callback=None
    ) -> List[Dict]:
        """Extract chapters from posts and attachments"""
        
        chapters = []
        
        for post_idx, post in enumerate(posts):
            try:
                post_id = post.get("id")
                attrs = post.get("attributes", {})
                post_title = attrs.get("title", "Untitled")
                post_content = attrs.get("content", "")
                post_type = attrs.get("post_type", "text_post")
                
                progress = 40 + (post_idx / len(posts)) * 40
                self._emit_progress(f"Processing: {post_title}", progress_callback, int(progress))
                
                # Parse text content
                if post_type == "text_post" and post_content:
                    extracted = self._parse_text_post(post_content, post_title)
                    chapters.extend(extracted)
                
                # Parse attachments
                relationships = post.get("relationships", {})
                attachments = relationships.get("attachments", {}).get("data", [])
                
                for attachment in attachments:
                    attachment_id = attachment.get("id")
                    headers = {"Authorization": f"Bearer {access_token}"}
                    
                    try:
                        response = requests.get(
                            f"{self.API_URL}/attachments/{attachment_id}",
                            headers=headers
                        )
                        response.raise_for_status()
                        attachment_data = response.json().get("data", {})
                        
                        download_url = attachment_data.get("attributes", {}).get("download_url")
                        filename = attachment_data.get("attributes", {}).get("filename", "attachment")
                        
                        if download_url:
                            file_path = os.path.join(output_dir, f"{post_id}_{filename}")
                            success = self._download_file(download_url, file_path)
                            
                            if success and filename.lower().endswith(".pdf"):
                                pdf_chapters = self._parse_pdf_file(file_path)
                                chapters.extend(pdf_chapters)
                    
                    except Exception as e:
                        logger.warning("Failed to process attachment: %s", e)
                        continue
            
            except Exception as e:
                logger.error("Failed to process post %s: %s", post.get("id"), e)
                continue
        
        return chapters
    
    def _parse_text_post(self, content: str, post_title: str) -> List[Dict]:
        """Parse text post for chapters"""
        
        # Clean HTML
        if "<" in content and ">" in content:
            extractor = HTMLTextExtractor()
            extractor.feed(content)
            content = extractor.get_text()
        
        content = content.strip()
        if not content:
            return []
        
        lines = content.split("\n")
        chapter_matches = self._find_chapter_headers(lines)
        
        if chapter_matches:
            # Multi-chapter post
            return self._split_by_headers(lines, chapter_matches)
        else:
            # Single chapter
            chapter_num = self._extract_chapter_number_from_title(post_title)
            return [{
                "number": chapter_num,
                "title": post_title,
                "content": content,
            }]
    
    def _parse_pdf_file(self, file_path: str) -> List[Dict]:
        """Parse PDF for chapters"""
        
        if not os.path.exists(file_path):
            logger.error("PDF not found: %s", file_path)
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
                else:
                    return [{
                        "number": 1,
                        "title": Path(file_path).stem,
                        "content": full_text.strip(),
                    }]
        
        except Exception as e:
            logger.error("Failed to parse PDF %s: %s", file_path, e)
            return []
    
    def _find_chapter_headers(self, lines: List[str]) -> List[tuple]:
        """Find chapter headers in lines"""
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
        """Split content by chapter headers"""
        chapters = []
        
        for i, (idx, chapter_num, title) in enumerate(matches):
            start = idx + 1
            end = matches[i + 1][0] if i + 1 < len(matches) else len(lines)
            
            content = "\n".join(lines[start:end]).strip()
            
            if content:
                chapters.append({
                    "number": chapter_num,
                    "title": title or f"Chapter {chapter_num}",
                    "content": content,
                })
        
        return chapters
    
    def _extract_chapter_number_from_title(self, title: str) -> int:
        """Extract chapter number from title"""
        match = re.search(r"\b(\d+)\b", title)
        return int(match.group(1)) if match else 1
    
    def _normalize_chapters(self, chapters: List[Dict]) -> List[Dict]:
        """Sort and deduplicate chapters"""
        
        chapters.sort(key=lambda x: x.get("number", 0))
        
        # Renumber sequentially if there are gaps
        for idx, ch in enumerate(chapters, 1):
            ch["number"] = idx
        
        return chapters
    
    # -------------------------
    # HELPERS
    # -------------------------
    def _emit_progress(self, message: str, callback=None, value: int = 0):
        """Emit progress"""
        if callback:
            callback(message, value)