import sqlite3
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path="data/novelcast.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()

            self.enable_wal()

            logger.info(
                "Database initialized",
                extra={"extra_data": {"db_path": db_path}},
            )

        except Exception:
            logger.exception("Failed to initialize database")
            raise

    
    def init_schema(self, schema_path="src/novelcast/db/schema.sql"):
        try:
            path = Path(schema_path)

            if not path.exists():
                raise FileNotFoundError(f"Schema file not found: {path}")

            sql = path.read_text(encoding="utf-8")

            self.conn.executescript(sql)
            self.conn.commit()

            logger.info("Database schema initialized")

        except Exception:
            logger.exception("Failed to initialize schema")
            raise
        
    # -------------------------
    # PERFORMANCE MODE
    # -------------------------
    def enable_wal(self):
        try:
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            self.conn.commit()

            logger.debug("WAL mode enabled")

        except Exception:
            logger.exception("Failed to enable WAL mode")
            raise

    # -------------------------
    # CORE EXECUTION (SAFE + LOGGED)
    # -------------------------
    def execute(self, query, params=()):
        start = time.perf_counter()

        try:
            logger.debug(
                "DB EXECUTE",
                extra={
                    "extra_data": {
                        "query": query,
                        "params": params,
                    }
                },
            )

            self.cursor.execute(query, params)
            self.conn.commit()

            return self.cursor

        except Exception:
            logger.exception(
                "Database execute failed",
                extra={
                    "extra_data": {
                        "query": query,
                        "params": params,
                    }
                },
            )
            raise

        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.debug(
                "DB EXECUTE COMPLETE",
                extra={"extra_data": {"duration_ms": round(duration, 2)}},
            )

    # -------------------------
    # FETCH ONE
    # -------------------------
    def fetchone(self, query, params=()):
        start = time.perf_counter()

        try:
            logger.debug(
                "DB FETCHONE",
                extra={"extra_data": {"query": query, "params": params}},
            )

            cur = self.cursor.execute(query, params)
            return cur.fetchone()

        except Exception:
            logger.exception(
                "Database fetchone failed",
                extra={"extra_data": {"query": query, "params": params}},
            )
            raise

        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.debug(
                "DB FETCHONE COMPLETE",
                extra={"extra_data": {"duration_ms": round(duration, 2)}},
            )

    # -------------------------
    # FETCH ALL
    # -------------------------
    def fetchall(self, query, params=()):
        start = time.perf_counter()

        try:
            logger.debug(
                "DB FETCHALL",
                extra={"extra_data": {"query": query, "params": params}},
            )

            cur = self.cursor.execute(query, params)
            return cur.fetchall()

        except Exception:
            logger.exception(
                "Database fetchall failed",
                extra={"extra_data": {"query": query, "params": params}},
            )
            raise

        finally:
            duration = (time.perf_counter() - start) * 1000
            logger.debug(
                "DB FETCHALL COMPLETE",
                extra={"extra_data": {"duration_ms": round(duration, 2)}},
            )


    # -------------------------
    # CLEAN SHUTDOWN
    # -------------------------
    def close(self):
        try:
            self.conn.close()
            logger.info("Database connection closed")

        except Exception:
            logger.exception("Error while closing database connection")