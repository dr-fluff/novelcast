# novelcast/db/repositories/progress_repository.py

from datetime import UTC, datetime

from sqlalchemy import select, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import aliased

from novelcast.db.models.chapter import Chapter, ChapterProgress
from novelcast.db.models.progress import ReadingProgress
from novelcast.db.repositories.base import BaseRepository

PROGRESS_USER_ID = "user_id"
PROGRESS_STORY_ID = "story_id"
PROGRESS_LAST_CHAPTER_ID = "last_chapter_id"
PROGRESS_LAST_CHAPTER_NUMBER = "last_chapter_number"
PROGRESS_LAST_POSITION = "last_position"
PROGRESS_FURTHEST_CHAPTER_ID = "furthest_chapter_id"
PROGRESS_FURTHEST_CHAPTER_NUMBER = "furthest_chapter_number"
PROGRESS_UPDATED_AT = "updated_at"
PROGRESS_PAGE = "page"
PROGRESS_ANCHOR = "anchor"


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
            return {PROGRESS_PAGE: row.page, PROGRESS_ANCHOR: row.anchor}

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

    def delete_progress(self, user_id: int, story_id: int) -> None:
        with self.session() as db:
            db.execute(
                delete(ReadingProgress).where(
                    ReadingProgress.user_id == user_id,
                    ReadingProgress.story_id == story_id,
                )
            )
            chapter_ids_subq = select(Chapter.id).where(Chapter.story_id == story_id)
            db.execute(
                delete(ChapterProgress).where(
                    ChapterProgress.user_id == user_id,
                    ChapterProgress.chapter_id.in_(chapter_ids_subq),
                )
            )
    def get_downloaded_listing_for_stories(self, story_ids: list[int]) -> list[dict]:
            if not story_ids:
                return []

            with self.session_no_commit() as db:
                rows = db.execute(
                    select(
                        Chapter.id,
                        Chapter.story_id,
                        Chapter.chapter_number,
                        Chapter.title,
                        Chapter.created_at,
                    )
                    .where(
                        Chapter.story_id.in_(story_ids),
                        Chapter.is_downloaded,
                    )
                    .order_by(Chapter.story_id, Chapter.chapter_number)
                ).all()
                return [
                    {
                        "id": row.id,
                        "story_id": row.story_id,
                        "chapter_number": row.chapter_number,
                        "title": row.title,
                        "url": None,
                        "file_path": None,
                        "is_downloaded": 1,
                        "created_at": row.created_at,
                    }
                    for row in rows
                ]

def _progress_to_dict(
    row: ReadingProgress | None,
    last_chapter_number: int | None = None,
    furthest_chapter_number: int | None = None,
) -> dict | None:
    if row is None:
        return None
    return {
        PROGRESS_USER_ID: row.user_id,
        PROGRESS_STORY_ID: row.story_id,
        PROGRESS_LAST_CHAPTER_ID: row.last_chapter_id,
        PROGRESS_LAST_CHAPTER_NUMBER: last_chapter_number,
        PROGRESS_LAST_POSITION: row.last_position,
        PROGRESS_FURTHEST_CHAPTER_ID: row.furthest_chapter_id,
        PROGRESS_FURTHEST_CHAPTER_NUMBER: furthest_chapter_number,
        PROGRESS_UPDATED_AT: row.updated_at,
    }
    
    