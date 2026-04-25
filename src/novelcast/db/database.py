import sqlite3
import logging
import time
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path="data/novelcast.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.enable_wal()

        logger.info(
            "Database initialized",
            extra={"extra_data": {"db_path": db_path}},
        )

    def init_schema(self, schema_path="src/novelcast/db/schema.sql"):

        path = Path(schema_path)

        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        sql = path.read_text(encoding="utf-8")

        self.conn.executescript(sql)
        self.conn.commit()
    
    # -------------------------
    # WAL MODE
    # -------------------------
    def enable_wal(self):
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.commit()

    # -------------------------
    # TRANSACTION CONTROL (IMPORTANT ADDITION)
    # -------------------------
    @contextmanager
    def transaction(self):
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # -------------------------
    # CORE EXECUTION
    # -------------------------
    def execute(self, query, params=()):
        start = time.perf_counter()

        try:
            cur = self.conn.execute(query, params)
            self.conn.commit()
            return cur.lastrowid   # 🔥 FIX HERE

        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.debug(f"EXEC {duration:.2f}ms")
    
    # -------------------------
    # BULK INSERT (CRITICAL FOR CHAPTERS)
    # -------------------------
    def executemany(self, query, seq_of_params):
        start = time.perf_counter()

        try:
            cur = self.conn.executemany(query, seq_of_params)
            self.conn.commit()
            return cur

        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.debug(f"EXEC MANY {duration:.2f}ms")

    # -------------------------
    # FETCH ONE
    # -------------------------
    def fetchone(self, query, params=()):
        cur = self.conn.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None

    # -------------------------
    # FETCH ALL
    # -------------------------
    def fetchall(self, query, params=()):
        cur = self.conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    # -------------------------
    # OPTIONAL: dict conversion helper (VERY USEFUL)
    # -------------------------
    def fetchall_dicts(self, query, params=()):
        cur = self.conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

    def fetchone_dict(self, query, params=()):
        row = self.conn.execute(query, params).fetchone()
        return dict(row) if row else None

    # -------------------------
    # CLEAN SHUTDOWN
    # -------------------------
    def close(self):
        self.conn.close()