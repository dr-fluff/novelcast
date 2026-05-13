# novelcast/db/repositories/progress_repository.py

from datetime import datetime, timezone

from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.progress import ReadingProgress


class ProgressRepository(BaseRepository):

    def get_progress(self, user_id: int, story_id: int) -> dict | None:
        with self.session_no_commit() as db:
            row = db.get(ReadingProgress, (user_id, story_id))
            return _progress_to_dict(row)

    def set_progress(
        self,
        user_id: int,
        story_id: int,
        last_chapter_id: int,
        last_position: int,
    ) -> None:
        with self.session() as db:
            stmt = (
                insert(ReadingProgress)
                .values(
                    user_id=user_id,
                    story_id=story_id,
                    last_chapter_id=last_chapter_id,
                    last_position=last_position,
                    updated_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "story_id"],
                    set_={
                        "last_chapter_id": last_chapter_id,
                        "last_position":   last_position,
                        "updated_at":      datetime.now(timezone.utc),
                    },
                )
            )
            db.execute(stmt)


def _progress_to_dict(row: ReadingProgress | None) -> dict | None:
    if row is None:
        return None
    return {
        "user_id":         row.user_id,
        "story_id":        row.story_id,
        "last_chapter_id": row.last_chapter_id,
        "last_position":   row.last_position,
        "updated_at":      row.updated_at,
    }
