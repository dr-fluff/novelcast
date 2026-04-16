# src/novelcast/storage/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path("data/novelcast.db")

class Database:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init()
        

    def _init(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            last_chapter INTEGER DEFAULT 0,
            requested_chapters INTEGER DEFAULT 0,
            cover_url TEXT
        )
        """)

        cur.execute("PRAGMA table_info(subscriptions)")
        columns = {row[1] for row in cur.fetchall()}
        if "requested_chapters" not in columns:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN requested_chapters INTEGER DEFAULT 0")
        if "cover_url" not in columns:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN cover_url TEXT")
        if "story_path" not in columns:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN story_path TEXT")
        if "downloaded_chapters" not in columns:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN downloaded_chapters INTEGER DEFAULT 0")
        if "available_chapters" not in columns:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN available_chapters INTEGER DEFAULT 0")
        self.conn.commit()

    def add_subscription(self, url, title="Unknown", last_chapter=0, requested_chapters=0, cover_url=None):
        self.conn.execute(
            "INSERT OR IGNORE INTO subscriptions (url, title, last_chapter, requested_chapters, cover_url) VALUES (?, ?, ?, ?, ?)",
            (url, title, last_chapter, requested_chapters, cover_url)
        )
        self.conn.commit()

    def update_cover_url(self, url, cover_url):
        self.conn.execute(
            "UPDATE subscriptions SET cover_url=? WHERE url=?",
            (cover_url, url)
        )
        self.conn.commit()

    def get_subscription(self, url):
        cur = self.conn.execute("SELECT id, url, title, last_chapter, requested_chapters, cover_url, story_path FROM subscriptions WHERE url = ?",(url,))
        row = cur.fetchone()
        if row is None:
            return None
        
        return {
            "id": row[0],
            "url": row[1],
            "title": row[2],
            "last_chapter": row[3],
            "requested_chapters": row[4],
            "cover_url": row[5],
            "story_path": row[6] if len(row) > 6 else None,
        }

    def get_subscriptions(self):
        cur = self.conn.execute(
            "SELECT id, url, title, last_chapter, requested_chapters, cover_url, story_path FROM subscriptions"
        )
        rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "url": r[1],
                "title": r[2],
                "last_chapter": r[3],
                "cover_url": r[4],
            }
            for r in rows
        ]

    def update_last_chapter(self, url, chapter):
        self.conn.execute(
            "UPDATE subscriptions SET last_chapter=? WHERE url=?",
            (chapter, url)
        )
        self.conn.commit()

    def update_requested_chapters(self, url, chapters):
        self.conn.execute(
            "UPDATE subscriptions SET requested_chapters=? WHERE url=?",
            (chapters, url)
        )
        self.conn.commit()