from pathlib import Path

class FileWriter:

    def write_story(self, story: dict) -> str:

        author = self._safe(story["author"])
        title = self._safe(story["title"])

        base = Path("library") / author / title
        base.mkdir(parents=True, exist_ok=True)

        for ch in story["chapters"]:
            path = base / f"chapter_{ch['number']}.html"

            path.write_text(ch["content"], encoding="utf-8")

            ch["file_path"] = str(path)

        return str(base)

    def _safe(self, name: str) -> str:
        return "".join(c for c in name if c.isalnum() or c in " _-").strip()