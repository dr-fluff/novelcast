# novelcast/db/repositories/chapters_repository.py

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import selectinload

from novelcast.db.models.chapter import Chapter, ChapterFile
from novelcast.db.repositories.base import BaseRepository


class ChaptersRepository(BaseRepository):
    # ── reads ─────────────────────────────────────────────────────────────

    def get_by_story(self, story_id: int) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(Chapter).where(Chapter.story_id == story_id).order_by(Chapter.chapter_number)
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
                    Chapter.is_downloaded,
                )
                .options(selectinload(Chapter.files))
                .order_by(Chapter.chapter_number)
            ).all()
            return [_to_dict(c) for c in rows]

    def get_downloaded_listing(self, story_id: int) -> list[dict]:
        """Return fields needed by the story chapter list without file joins."""
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
                    Chapter.story_id == story_id,
                    Chapter.is_downloaded,
                )
                .order_by(Chapter.chapter_number)
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

    def get_downloaded_listing_for_stories(self, story_ids: list[int]) -> list[dict]:
        """Bulk variant of get_downloaded_listing() for many stories in one
        query — used by pages that render the whole library (e.g. index),
        so they don't run one query per story."""
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

    def get_downloaded_ids(self, story_id: int) -> list[int]:
        with self.session_no_commit() as db:
            return list(
                db.scalars(
                    select(Chapter.id)
                    .where(
                        Chapter.story_id == story_id,
                        Chapter.is_downloaded,
                    )
                    .order_by(Chapter.chapter_number)
                ).all()
            )

    def get_chapter_numbers(self, story_id: int) -> set[int]:
        with self.session_no_commit() as db:
            return set(db.scalars(select(Chapter.chapter_number).where(Chapter.story_id == story_id)).all())

    def get_downloaded_numbers(self, story_id: int) -> set[int]:
        with self.session_no_commit() as db:
            return set(
                db.scalars(
                    select(Chapter.chapter_number).where(
                        Chapter.story_id == story_id,
                        Chapter.is_downloaded,
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
        file_path: str | None,
        is_downloaded: int,
    ) -> None:
        with self.session() as db:
            chapter = None

            # A source URL is the strongest available identity when present.
            if url:
                chapter = db.scalars(
                    select(Chapter).where(Chapter.url == url)
                ).first()

            # Do not reassign a URL that already belongs to another story.
            if chapter is not None and chapter.story_id != story_id:
                return

            if chapter is None:
                # A chapter without a URL cannot use the URL uniqueness
                # constraint. Fall back to the story and chapter number.
                if url is None:
                    chapter = db.scalars(
                        select(Chapter).where(
                            Chapter.story_id == story_id,
                            Chapter.chapter_number == chapter_number,
                            Chapter.url.is_(None),
                        )
                    ).first()

                if chapter is None:
                    chapter = Chapter(
                        story_id=story_id,
                        chapter_number=chapter_number,
                        title=title,
                        url=url,
                        is_downloaded=bool(is_downloaded),
                    )
                    db.add(chapter)
                    db.flush()
            else:
                chapter.chapter_number = chapter_number
                chapter.title = title
                chapter.is_downloaded = bool(is_downloaded)

            if not file_path:
                return

            # Reuse a matching HTML record instead of creating duplicates.
            existing_file = db.scalars(
                select(ChapterFile).where(
                    ChapterFile.chapter_id == chapter.id,
                    ChapterFile.file_path == file_path,
                    ChapterFile.format == "html",
                )
            ).first()

            if existing_file:
                existing_file.is_canonical = True
                for other_file in chapter.files:
                    if other_file.id != existing_file.id and other_file.format == "html":
                        other_file.is_canonical = False
            else:
                # Keep other file records intact. Make the new HTML file
                # canonical without deleting unrelated formats.
                for other_file in chapter.files:
                    if other_file.format == "html":
                        other_file.is_canonical = False

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