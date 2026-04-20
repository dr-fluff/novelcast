import sqlite3
from pathlib import Path
import re

class Database:
    def __init__(self, db_path="data/novelcast.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.enable_wal()

    def enable_wal(self):
        self.cursor.execute("PRAGMA journal_mode=WAL;")
        self.conn.commit()

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()

    def fetchone(self, query, params=()):
        cur = self.cursor.execute(query, params)
        return cur.fetchone()

    def fetchall(self, query, params=()):
        cur = self.cursor.execute(query, params)
        return cur.fetchall()

    def close(self):
        self.conn.close()