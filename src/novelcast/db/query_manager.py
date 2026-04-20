import re
from pathlib import Path


class QueryManager:
    def __init__(self, db, queries_dir="novelcast/db/queries"):
        self.db = db
        self.queries = {}
        self.load_queries(queries_dir)

    def load_queries(self, queries_dir):
        queries_dir = Path(queries_dir)

        for file in queries_dir.glob("*.sql"):
            self._parse_file(file)

    def _parse_file(self, file_path):
        content = file_path.read_text()

        pattern = r"--\s*name:\s*(\w+)\s*(.*?)((?=--\s*name:)|\Z)"
        matches = re.findall(pattern, content, re.S)

        for name, sql, _ in matches:
            key = f"{file_path.stem}.{name}"
            self.queries[key] = sql.strip()

    def run(self, name, params=()):
        self.db.execute(self.queries[name], params)

    def fetchone(self, name, params=()):
        return self.db.fetchone(self.queries[name], params)

    def fetchall(self, name, params=()):
        return self.db.fetchall(self.queries[name], params)