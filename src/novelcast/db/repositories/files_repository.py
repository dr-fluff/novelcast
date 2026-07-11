# ─────────────────────────────────────────────────────────────────────────────
# novelcast/db/repositories/files_repository.py
#
# NOTE: There is no `files` table in the current schema.
# ChapterFile (chapter_files table) is the equivalent.
# This repo is a stub — wire it properly once ChapterFile is in use.
# ─────────────────────────────────────────────────────────────────────────────

from novelcast.db.models.chapter import ChapterFile
from novelcast.db.repositories.base import BaseRepository


class FilesRepository(BaseRepository):
    def get_by_id(self, file_id: int) -> dict | None:
        with self.session_no_commit() as db:
            row = db.get(ChapterFile, file_id)
            return _file_to_dict(row)

    def update_metadata(self, file_id: int, size: int) -> None:
        # ChapterFile doesn't have a size column yet — add when needed.
        # For now this is a no-op so existing callers don't break.
        pass


def _file_to_dict(row: ChapterFile | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "chapter_id": row.chapter_id,
        "file_path": row.file_path,
        "format": row.format,
        "is_canonical": row.is_canonical,
        "created_at": row.created_at,
    }
