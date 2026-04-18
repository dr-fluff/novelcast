import sqlite3
from pathlib import Path

DB_PATH = Path("data/novelcast.db")
MIGRATIONS_DIR = Path("src/novelcast/storage/migrations")


class Database:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._init_migrations()
        self.run_migrations()

    # ─────────────────────────────
    # MIGRATION SYSTEM BOOTSTRAP
    # ─────────────────────────────
    def _init_migrations(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)

        self.conn.commit()

    def run_migrations(self):
        cur = self.conn.cursor()

        applied = {
            row["name"]
            for row in cur.execute("SELECT name FROM migrations")
        }

        for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if file.name in applied:
                continue

            sql = file.read_text(encoding="utf-8")
            cur.executescript(sql)

            cur.execute(
                "INSERT INTO migrations (name) VALUES (?)",
                (file.name,)
            )

            self.conn.commit()

    # ─────────────────────────────
    # SUBSCRIPTIONS (runtime logic only)
    # ─────────────────────────────
    def add_subscription(self, url, title="Unknown", last_chapter=0,
                         requested_chapters=0, cover_url=None):

        self.conn.execute("""
            INSERT OR IGNORE INTO subscriptions
            (url, title, last_chapter, requested_chapters, cover_url)
            VALUES (?, ?, ?, ?, ?)
        """, (url, title, last_chapter, requested_chapters, cover_url))

        self.conn.commit()

    def get_subscription(self, url):
        cur = self.conn.execute("""
            SELECT *
            FROM subscriptions
            WHERE url = ?
        """, (url,))

        row = cur.fetchone()
        return dict(row) if row else None

    def get_subscriptions(self):
        cur = self.conn.execute("SELECT * FROM subscriptions")
        return [dict(r) for r in cur.fetchall()]

    def update_last_chapter(self, url, chapter):
        self.conn.execute("""
            UPDATE subscriptions
            SET last_chapter = ?
            WHERE url = ?
        """, (chapter, url))
        self.conn.commit()

    def update_requested_chapters(self, url, chapters):
        self.conn.execute("""
            UPDATE subscriptions
            SET requested_chapters = ?
            WHERE url = ?
        """, (chapters, url))
        self.conn.commit()

    def update_cover_url(self, url, cover_url):
        self.conn.execute("""
            UPDATE subscriptions
            SET cover_url = ?
            WHERE url = ?
        """, (cover_url, url))
        self.conn.commit()

    # ─────────────────────────────
    # SETTINGS (moved to migrations too)
    # ─────────────────────────────
    def get_settings(self):
        cur = self.conn.execute("""
            SELECT theme, font_size, sort
            FROM settings
            WHERE user_id = 1
        """)
        row = cur.fetchone()

        return dict(row) if row else {
            "theme": "light",
            "font_size": 16,
            "sort": "title",
        }

    def update_settings(self, theme=None, font_size=None, sort=None):
        current = self.get_settings()

        self.conn.execute("""
            UPDATE settings
            SET theme = ?, font_size = ?, sort = ?
            WHERE user_id = 1
        """, (
            theme or current["theme"],
            font_size or current["font_size"],
            sort or current["sort"],
        ))

        self.conn.commit()