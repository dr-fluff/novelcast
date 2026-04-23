from pathlib import Path

BASE_DIR = Path("data")


class FileService:
    def __init__(self, repo):
        self.repo = repo

    def get_file_content(self, file_id: int) -> str:
        file = self.repo.get_by_id(file_id)

        if not file:
            raise FileNotFoundError("File not found in DB")

        path = BASE_DIR / file["path"]

        if not path.exists():
            raise FileNotFoundError("File missing on disk")

        return path.read_text()

    def update_file(self, file_id: int, content: str):
        file = self.repo.get_by_id(file_id)

        if not file:
            raise FileNotFoundError("File not found in DB")

        path = BASE_DIR / file["path"]
        path.write_text(content)

        self.repo.update_metadata(file_id, len(content))