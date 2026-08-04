# novelcast/db/repositories/progress_repository.py

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import aliased

from novelcast.db.models.chapter import Chapter, ChapterProgress
from novelcast.db.models.progress import ReadingProgress
from novelcast.db.repositories.base import BaseRepository


class ProgressRepository(BaseRepository):
    def get_progress(self, user_id: int, story_id: int) -> dict | None:
        with self.session_no_commit() as db:
            row = db.get(ReadingProgress, (user_id, story_id))
            return _progress_to_dict(row)

    def get_all_for_user(self, user_id: int) -> list[dict]:
        LastChapter = aliased(Chapter)
        FurthestChapter = aliased(Chapter)

        with self.session_no_commit() as db:
            rows = db.execute(
                select(
                    ReadingProgress,
                    LastChapter.chapter_number.label("last_chapter_number"),
                    FurthestChapter.chapter_number.label("furthest_chapter_number"),
                )
                .outerjoin(LastChapter, LastChapter.id == ReadingProgress.last_chapter_id)
                .outerjoin(FurthestChapter, FurthestChapter.id == ReadingProgress.furthest_chapter_id)
                .where(ReadingProgress.user_id == user_id)
            ).all()
            return [
                _progress_to_dict(
                    row,
                    last_chapter_number=last_chapter_number,
                    furthest_chapter_number=furthest_chapter_number,
                )
                for row, last_chapter_number, furthest_chapter_number in rows
            ]

    def set_progress(
        self,
        user_id: int,
        story_id: int,
        last_chapter_id: int,
        last_position: int,
    ) -> None:
        """Unconditionally sets the 'continue reading' pointer to wherever
        the user most recently read — no forward-only guard. This is
        intentionally different from advance_furthest_chapter(): reading
        an earlier chapter should move this pointer there, even though
        it shouldn't affect what's considered "furthest reached" for
        unread tracking."""
        with self.session() as db:
            stmt = (
                insert(ReadingProgress)
                .values(
                    user_id=user_id,
                    story_id=story_id,
                    last_chapter_id=last_chapter_id,
                    last_position=last_position,
                    updated_at=datetime.now(UTC),
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "story_id"],
                    set_={
                        "last_chapter_id": last_chapter_id,
                        "last_position": last_position,
                        "updated_at": datetime.now(UTC),
                    },
                )
            )
            db.execute(stmt)

    def advance_furthest_chapter(
        self,
        user_id: int,
        story_id: int,
        chapter_id: int,
        last_position: int,
    ) -> None:
        """Forward-only: only ever moves furthest_chapter_id up, never
        back. This is what read/unread marking on the story page relies
        on, so re-reading an earlier chapter must never regress it. The
        guard is expressed directly in the upsert's WHERE clause so the
        check-then-write happens atomically in the database rather than
        as two round trips from Python."""
        with self.session() as db:
            stmt = (
                insert(ReadingProgress)
                .values(
                    user_id=user_id,
                    story_id=story_id,
                    furthest_chapter_id=chapter_id,
                    last_position=last_position,
                    updated_at=datetime.now(UTC),
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "story_id"],
                    set_={
                        "furthest_chapter_id": chapter_id,
                        "updated_at": datetime.now(UTC),
                    },
                    where=(
                        (ReadingProgress.furthest_chapter_id.is_(None))
                        | (ReadingProgress.furthest_chapter_id < chapter_id)
                    ),
                )
            )
            db.execute(stmt)

    def get_chapter_page(self, user_id: int, chapter_id: int) -> dict | None:
        with self.session_no_commit() as db:
            row = db.scalars(
                select(ChapterProgress).where(
                    ChapterProgress.user_id == user_id,
                    ChapterProgress.chapter_id == chapter_id,
                )
            ).first()
            if not row:
                return None
            return {"page": row.page, "anchor": row.anchor}

    def set_chapter_page(self, user_id: int, chapter_id: int, page: int, anchor: int) -> None:
        with self.session() as db:
            stmt = (
                insert(ChapterProgress)
                .values(user_id=user_id, chapter_id=chapter_id, page=page, anchor=anchor)
                .on_conflict_do_update(
                    index_elements=["user_id", "chapter_id"],
                    set_={
                        "page": page,
                        "anchor": anchor,
                        "updated_at": datetime.now(UTC),
                    },
                )
            )
            db.execute(stmt)


def _progress_to_dict(
    row: ReadingProgress | None,
    last_chapter_number: int | None = None,
    furthest_chapter_number: int | None = None,
) -> dict | None:
    if row is None:
        return None
    return {
        "user_id": row.user_id,
        "story_id": row.story_id,
        "last_chapter_id": row.last_chapter_id,
        "last_chapter_number": last_chapter_number,
        "last_position": row.last_position,
        "furthest_chapter_id": row.furthest_chapter_id,
        "furthest_chapter_number": furthest_chapter_number,
        "updated_at": row.updated_at,
    }
