# ─────────────────────────────────────────────────────────────────────────────
# novelcast/db/repositories/files_repository.py
#
# NOTE: There is no `files` table in the current schema.
# ChapterFile (chapter_files table) is the equivalent.
# This repo is a stub — wire it properly once ChapterFile is in use.
# ─────────────────────────────────────────────────────────────────────────────

from novelcast.db.models.chapter import ChapterFile
from novelcast.db.repositories.base import BaseRepository

FILE_ID = "id"
FILE_CHAPTER_ID = "chapter_id"
FILE_PATH = "file_path"
FILE_FORMAT = "format"
FILE_IS_CANONICAL = "is_canonical"
FILE_CREATED_AT = "created_at"


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
        FILE_ID: row.id,
        FILE_CHAPTER_ID: row.chapter_id,
        FILE_PATH: row.file_path,
        FILE_FORMAT: row.format,
        FILE_IS_CANONICAL: row.is_canonical,
        FILE_CREATED_AT: row.created_at,
    }
