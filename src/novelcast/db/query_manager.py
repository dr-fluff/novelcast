import re
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class QueryManager:
    """
    ONLY responsibility:
    - load SQL files
    - provide raw SQL by key
    """

    def __init__(self, db, queries_dir: str | Path | None = None):
        self.db = db

        base_dir = Path(__file__).resolve().parent
        self.queries_dir = Path(queries_dir) if queries_dir else base_dir / "queries"

        self._queries: Dict[str, str] = {}

        self._load()

    def _load(self):
        for file in self.queries_dir.glob("*.sql"):
            self._parse_file(file)

        logger.info("SQL loaded", extra={"count": len(self._queries)})

    def _parse_file(self, file_path: Path):
        content = file_path.read_text(encoding="utf-8")

        pattern = r"--\s*name:\s*(\w+)\s*(.*?)(?=--\s*name:|\Z)"
        matches = re.findall(pattern, content, re.S)

        namespace = file_path.stem

        for name, sql in matches:
            key = f"{namespace}.{name}"
            self._queries[key] = sql.strip()

    def sql(self, key: str) -> str:
        if key not in self._queries:
            raise KeyError(f"SQL not found: {key}")
        return self._queries[key]