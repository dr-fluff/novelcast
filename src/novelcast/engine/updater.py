from pathlib import Path
import re
import subprocess
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen


class UpdateEngine:
    def __init__(self, db):
        self.db = db
        self.base = Path("data/stories")
        self.base.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────
    # helpers
    # ─────────────────────────────
    def _safe_filename(self, value: str) -> str:
        value = re.sub(r'[<>:"/\\|?*]', '', value)
        return re.sub(r'\s+', '_', value).strip('_')

    def _extract_metadata(self, html: str):
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1")
        if not h1:
            return "Unknown", "Unknown"

        text = h1.get_text(" ", strip=True)

        if " by " in text:
            title, author = text.rsplit(" by ", 1)
        else:
            title, author = text, "Unknown"

        return title.strip(), author.strip()

    def _get_fiction_dir(self, title: str, author: str) -> Path:
        return self.base / self._safe_filename(author) / self._safe_filename(title)

    # ─────────────────────────────
    # MAIN DOWNLOAD (initial + updates)
    # ─────────────────────────────
    def download_story(self, url: str, cover_url: str | None = None):

        story_file = self.base / self._safe_filename(url)

        result = subprocess.run([
            "fanficfare",
            "--non-interactive",
            "-f", "html",
            "-o", f"output_filename={story_file}",
            url
        ], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return False, result.stderr.strip()

        html = story_file.read_text(encoding="utf-8", errors="ignore")
        title, author = self._extract_metadata(html)

        fiction_dir = self._get_fiction_dir(title, author)
        fiction_dir.mkdir(parents=True, exist_ok=True)

        # save stable path in DB (IMPORTANT FIX)
        self.db.conn.execute("""
            INSERT INTO subscriptions (url, title, story_path, last_chapter, requested_chapters, cover_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                story_path=excluded.story_path,
                cover_url=excluded.cover_url
        """, (
            url,
            title,
            str(fiction_dir),
            0,
            0,
            cover_url
        ))

        self.db.conn.commit()

        # split chapters incrementally
        ok, err, new_count = self._split_chapters(story_file, fiction_dir)
        if not ok:
            return False, err

        downloaded_total = self._count_downloaded_chapters(fiction_dir)

        # update DB stats
        self.db.conn.execute("""
            UPDATE subscriptions
            SET downloaded_chapters = ?
            WHERE url = ?
        """, (downloaded_total, url))

        self.db.conn.commit()

        story_file.unlink(missing_ok=True)

        return True, f"Downloaded {new_count} new chapters"

    # ─────────────────────────────
    # CHAPTER SPLITTER (INCREMENTAL SAFE)
    # ─────────────────────────────
    def _split_chapters(self, story_file: Path, fiction_dir: Path):

        try:
            html = story_file.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            sections = soup.find_all("a", attrs={"name": re.compile(r"^section\d+$")})

            if not sections:
                return False, "No chapters found", 0

            existing = {f.name for f in fiction_dir.glob("*.html")}

            new_count = 0

            for i, anchor in enumerate(sections, 1):

                chapter_title = anchor.get_text(strip=True) or f"Chapter {i}"
                file_name = self._safe_filename(chapter_title)

                chapter_file = fiction_dir / f"{i:03d}-{file_name}.html"

                # ONLY NEW FILES
                if chapter_file.name in existing:
                    continue

                content = [str(anchor)]
                for sib in anchor.next_siblings:
                    if getattr(sib, "name", None) == "a" and sib.get("name", "").startswith("section"):
                        break
                    content.append(str(sib))

                chapter_html = f"""
                <html>
                <head><meta charset="utf-8"><title>{chapter_title}</title></head>
                <body>{''.join(content)}</body>
                </html>
                """

                chapter_file.write_text(chapter_html, encoding="utf-8")
                new_count += 1

            return True, "", new_count

        except Exception as e:
            return False, str(e), 0

    # ─────────────────────────────
    # UPDATE CHECKER (TRUE VERSION)
    # ─────────────────────────────
    def check_updates(self, status_callback=None):
        subs = self.db.get_subscriptions()

        for sub in subs:
            url = sub["url"]
            status_msg = f"🔍 Checking {url}"
            if status_callback:
                status_callback(status_msg, f"Checking {url}")

            available = self.refresh_available_chapters(url)
            downloaded = self._count_downloaded_chapters_from_db(sub)

            status_msg = f"📦 Available: {available}"
            if status_callback:
                status_callback(f"📦 Available: {available}", f"Checking {url}")

            status_msg = f"💾 Downloaded: {downloaded}"
            if status_callback:
                status_callback(f"💾 Downloaded: {downloaded}", f"Checking {url}")

            if available is None:
                status_msg = "❌ Failed to fetch available chapters"
                if status_callback:
                    status_callback(status_msg, f"Checking {url}")
                continue

            missing = available - downloaded

            if missing <= 0:
                status_msg = "✅ Up to date"
                if status_callback:
                    status_callback(status_msg, f"Checking {url}")
                continue

            status_msg = f"⬇️ Missing {missing} chapters → downloading"
            if status_callback:
                status_callback(status_msg, f"Downloading {url}")

            ok, msg = self.download_story(url)

            if ok:
                status_msg = f"✅ Updated: {msg}"
                print(status_msg)
                if status_callback:
                    status_callback(status_msg, f"Updated {url}")
            else:
                status_msg = f"❌ Failed: {msg}"
                print(status_msg)
                if status_callback:
                    status_callback(status_msg, f"Failed to update {url}")

    # ─────────────────────────────
    # AVAILABLE CHAPTERS SCRAPER
    # ─────────────────────────────
    def refresh_available_chapters(self, url: str):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html = urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "html.parser")

            # better heuristic than raw <a> count
            chapters = len(soup.find_all("a", attrs={"href": True}))

            self.db.conn.execute("""
                UPDATE subscriptions
                SET available_chapters = ?
                WHERE url = ?
            """, (chapters, url))

            self.db.conn.commit()

            return chapters

        except Exception as e:
            print("refresh failed:", e)
            return None

    # ─────────────────────────────
    # DOWNLOAD COUNTER (TRUTH = FILESYSTEM)
    # ─────────────────────────────
    def _count_downloaded_chapters_from_db(self, sub: dict) -> int:
        path = sub.get("story_path")
        if not path:
            return 0

        return len(list(Path(path).glob("*.html")))

    def _count_downloaded_chapters(self, fiction_dir: Path) -> int:
        if not fiction_dir.exists():
            return 0
        return len(list(fiction_dir.glob("*.html")))