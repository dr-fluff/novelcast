# novelcast/utils/files.py

import re
from pathlib import Path

class FileUtils:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir).resolve()
        
    def safe(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        return re.sub(r'\s+', '_', name).strip('_')
    
    def story_dir(self, author: str | None, title: str | None) -> Path:
        safe_author = self._safe(author or "Unknown_Author")
        safe_title = self._safe(title or "Unknown_Title")
        path = self.base_dir / safe_author / safe_title
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_chapter(self, path: Path, filename: str, content: str):
        file_path = path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _safe(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")