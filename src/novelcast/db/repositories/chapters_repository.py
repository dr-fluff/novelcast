# novelcast/db/repositories/chapters_repository.py

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.chapter import Chapter, ChapterFile


class ChaptersRepository(BaseRepository):

    # ── reads ─────────────────────────────────────────────────────────────

    def get_by_story(self, story_id: int) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(Chapter)
                .where(Chapter.story_id == story_id)
                .order_by(Chapter.chapter_number)
            ).all()
            return [_to_dict(c) for c in rows]

    def get_by_number(self, story_id: int, chapter_number: int) -> dict | None:
        with self.session_no_commit() as db:
            row = db.scalars(
                select(Chapter).where(
                    Chapter.story_id == story_id,
                    Chapter.chapter_number == chapter_number,
                )
            ).first()
            return _to_dict(row)

    def get_by_id(self, chapter_id: int) -> dict | None:
        with self.session_no_commit() as db:
            return _to_dict(db.get(Chapter, chapter_id))

    def get_downloaded(self, story_id: int) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(Chapter)
                .where(
                    Chapter.story_id == story_id,
                    Chapter.is_downloaded == True,
                )
                .order_by(Chapter.chapter_number)
            ).all()
            return [_to_dict(c) for c in rows]

    def get_downloaded_ids(self, story_id: int) -> list[int]:
        with self.session_no_commit() as db:
            return list(
                db.scalars(
                    select(Chapter.id).where(
                        Chapter.story_id == story_id,
                        Chapter.is_downloaded == True,
                    ).order_by(Chapter.chapter_number)
                ).all()
            )

    def get_chapter_numbers(self, story_id: int) -> set[int]:
        with self.session_no_commit() as db:
            return set(
                db.scalars(
                    select(Chapter.chapter_number).where(
                        Chapter.story_id == story_id
                    )
                ).all()
            )

    def get_downloaded_numbers(self, story_id: int) -> set[int]:
        with self.session_no_commit() as db:
            return set(
                db.scalars(
                    select(Chapter.chapter_number).where(
                        Chapter.story_id == story_id,
                        Chapter.is_downloaded == True,
                    )
                ).all()
            )

    # ── writes ────────────────────────────────────────────────────────────

    def create(
        self,
        story_id: int,
        chapter_number: int,
        title: str | None,
        url: str | None,
        file_path: str | None = None,
        is_downloaded: int = 0,
    ) -> int:
        with self.session() as db:
            chapter = Chapter(
                story_id=story_id,
                chapter_number=chapter_number,
                title=title,
                url=url,
                is_downloaded=bool(is_downloaded),
            )
            db.add(chapter)
            db.flush()

            if file_path:
                db.add(
                    ChapterFile(
                        chapter_id=chapter.id,
                        file_path=file_path,
                        format="html",
                        is_canonical=True,
                    )
                )

            return chapter.id

    def upsert(
        self,
        story_id: int,
        chapter_number: int,
        title: str | None,
        url: str | None,
        file_path: str | None = None,
        is_downloaded: int = 0,
    ) -> None:
        with self.session() as db:

            stmt = (
                insert(Chapter)
                .values(
                    story_id=story_id,
                    chapter_number=chapter_number,
                    title=title,
                    url=url,
                    is_downloaded=bool(is_downloaded),
                )
                .on_conflict_do_update(
                    index_elements=["url"],
                    set_={
                        "story_id": story_id,
                        "chapter_number": chapter_number,
                        "title": title,
                        "is_downloaded": bool(is_downloaded),
                    },
                )
            )

            db.execute(stmt)

            # If we have file_path, attach it separately
            if file_path:
                chapter = db.scalars(
                    select(Chapter).where(Chapter.url == url)
                ).first()

                if chapter:
                    # optionally clear previous canonical file
                    for f in chapter.files:
                        if f.is_canonical:
                            f.is_canonical = False

                    db.add(
                        ChapterFile(
                            chapter_id=chapter.id,
                            file_path=file_path,
                            format="html",
                            is_canonical=True,
                        )
                    )

    def upsert_bulk(self, chapters: list[dict]) -> None:
        """Bulk upsert chapters (Chapter only). ChapterFile handled separately."""
        if not chapters:
            return

        with self.session() as db:
            db.execute(
                insert(Chapter),
                chapters,
            )

    def mark_downloaded(
        self,
        story_id: int,
        chapter_number: int,
        file_path: str,
    ) -> None:
        with self.session() as db:
            chapter = db.scalars(
                select(Chapter).where(
                    Chapter.story_id == story_id,
                    Chapter.chapter_number == chapter_number,
                )
            ).first()

            if not chapter:
                return

            chapter.is_downloaded = True

            # optional: deactivate previous canonical files
            for f in chapter.files:
                f.is_canonical = False

            db.add(
                ChapterFile(
                    chapter_id=chapter.id,
                    file_path=file_path,
                    format="html",
                    is_canonical=True,
                )
            )


# ── helper ────────────────────────────────────────────────────────────────

def _to_dict(chapter: Chapter | None) -> dict | None:
    if chapter is None:
        return None

    html_file = next(
        (f for f in chapter.files if f.is_canonical),
        None,
    )

    return {
        "id": chapter.id,
        "story_id": chapter.story_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "url": chapter.url,
        "file_path": html_file.file_path if html_file else None,
        "is_downloaded": int(chapter.is_downloaded),
        "created_at": chapter.created_at,
    }