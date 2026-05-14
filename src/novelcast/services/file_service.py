# novelcast/services/file_service.py

from pathlib import Path


class FileService:
    def __init__(self, repo, base_dir: str | Path = "data"):
        self.repo = repo
        self.base_dir = Path(base_dir)

    def _resolve(self, file_id: int) -> tuple[dict, Path]:
        file = self.repo.get_by_id(file_id)
        if not file:
            raise FileNotFoundError(f"File {file_id} not found in DB")

        path = self.base_dir / file["path"]
        if not path.exists():
            raise FileNotFoundError(f"File {file_id} missing on disk: {path}")

        return file, path

    def get_file_content(self, file_id: int) -> str:
        _, path = self._resolve(file_id)
        return path.read_text()

    def update_file(self, file_id: int, content: str) -> None:
        _, path = self._resolve(file_id)
        path.write_text(content)
        self.repo.update_metadata(file_id, len(content))