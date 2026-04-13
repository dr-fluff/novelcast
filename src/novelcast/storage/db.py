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
            last_chapter INTEGER DEFAULT 0
        )
        """)

        self.conn.commit()

    def add_subscription(self, url, title="Unknown"):
        self.conn.execute(
            "INSERT OR IGNORE INTO subscriptions (url, title) VALUES (?, ?)",
            (url, title)
        )
        self.conn.commit()

    def get_subscriptions(self):
        return self.conn.execute(
            "SELECT id, url, title, last_chapter FROM subscriptions"
        ).fetchall()

    def update_last_chapter(self, url, chapter):
        self.conn.execute(
            "UPDATE subscriptions SET last_chapter=? WHERE url=?",
            (chapter, url)
        )
        self.conn.commit()