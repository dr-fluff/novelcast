from novelcast.core.context import AppContext
from pathlib import Path

BASE_DIR = Path("data")


class FileService:
    def __init__(self):
        self.qm = AppContext().qm

    def get_file_content(self, file_id):
        file = self.qm.fetchone("files.get_by_id", (file_id,))
        path = BASE_DIR / file["path"]
        return path.read_text()

    def update_file(self, file_id, content):
        file = self.qm.fetchone("files.get_by_id", (file_id,))
        path = BASE_DIR / file["path"]

        path.write_text(content)

        self.qm.run("files.update_metadata", (len(content), file_id))