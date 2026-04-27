# novelcast/utils/files.py

import re
from pathlib import Path

class FileUtils:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        
    def safe(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        return re.sub(r'\s+', '_', name).strip('_')
    
    def story_dir(self, author: str, title: str) -> Path:
        path = self.base_dir / self._safe(author) / self._safe(title)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_chapter(self, path: Path, filename: str, content: str):
        file_path = path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _safe(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")