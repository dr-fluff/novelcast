# novelcast/utils/files.py

import re
from pathlib import Path


class FileUtils:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir).resolve()

    def safe(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        return re.sub(r"\s+", "_", name).strip("_")

    def story_dir(
        self,
        author: str | None,
        title: str | None,
        reserved_paths: set[str] | None = None,
        preferred_path: str | None = None,
    ) -> Path:
        safe_author = self._safe(author or "Unknown_Author")
        safe_title = self._safe(title or "Unknown_Title")
        path = self.base_dir / safe_author / safe_title

        reserved = {str(Path(p).resolve()) for p in (reserved_paths or set())}

        if preferred_path:
            preferred = Path(preferred_path).resolve()
            if str(preferred) not in reserved:
                preferred.mkdir(parents=True, exist_ok=True)
                return preferred

        candidate = path.resolve()
        suffix = 2
        while str(candidate) in reserved or candidate.exists():
            candidate = path.parent / f"{path.name}_{suffix}"
            suffix += 1

        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    def write_chapter(self, path: Path, filename: str, content: str):
        file_path = path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def _safe(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")

    def dir_size(self, path: Path) -> int:
        """Return total size in bytes for files under path."""
        try:
            total = 0
            for p in path.rglob("*"):
                if p.is_file():
                    try:
                        total += p.stat().st_size
                    except Exception:
                        # ignore files we can't stat
                        continue
            return int(total)
        except Exception:
            return 0


def human_readable_size(num: int) -> str:
    """Convert bytes to human readable string."""
    if num is None:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0:
            return f"{num:.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"
