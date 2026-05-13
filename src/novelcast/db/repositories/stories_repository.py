# novelcast/db/repositories/stories_repository.py

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.story import Story
from novelcast.db.models.chapter import Chapter


class StoriesRepository(BaseRepository):

    # ── reads ─────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        with self.session_no_commit() as db:
            stories = db.scalars(select(Story).order_by(Story.created_at.desc())).all()
            return [_to_dict(s) for s in stories]

    def get_by_id(self, story_id: int) -> dict | None:
        with self.session_no_commit() as db:
            return _to_dict(db.get(Story, story_id))

    def get_by_url(self, url: str) -> dict | None:
        with self.session_no_commit() as db:
            story = db.scalars(select(Story).where(Story.source_url == url)).first()
            return _to_dict(story)

    def get_chapter_file_paths(self, story_id: int) -> list[str]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(Chapter.file_path).where(
                    Chapter.story_id == story_id,
                    Chapter.file_path.isnot(None),
                    Chapter.file_path != "",
                )
            ).all()
            return list(rows)

    def get_chapter_numbers(self, story_id: int) -> list[int]:
        with self.session_no_commit() as db:
            return list(db.scalars(
                select(Chapter.chapter_number).where(Chapter.story_id == story_id)
            ).all())

    # ── writes ────────────────────────────────────────────────────────────

    def create(self, title: str, author: str | None, url: str | None) -> int:
        with self.session() as db:
            story = Story(title=title, author=author, source_url=url)
            db.add(story)
            db.flush()
            return story.id

    def upsert(self, title: str, author: str | None, url: str) -> None:
        with self.session() as db:
            stmt = (
                insert(Story)
                .values(title=title, author=author, source_url=url)
                .on_conflict_do_update(
                    index_elements=["source_url"],
                    set_={
                        "title": title,
                        "author": author,
                        "last_updated": datetime.now(timezone.utc),
                    },
                )
            )
            db.execute(stmt)

    def update_metadata(self, story_id: int, title: str, author: str | None) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                story.title = title
                story.author = author
                story.last_updated = datetime.now(timezone.utc)

    def update_paths(self, story_id: int, local_path: str, cover_path: str | None = None) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                story.local_path = local_path
                story.cover_path = cover_path

    def update_chapter_stats(
        self,
        story_id: int,
        total_chapters: int,
        downloaded_chapters: int,
        latest_downloaded_chapter: int | None = None,
        latest_online_chapter: int | None = None,
        online_chapters: int | None = None,
    ) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                story.total_chapters = total_chapters
                story.downloaded_chapters = downloaded_chapters
                story.latest_downloaded_chapter = latest_downloaded_chapter
                story.latest_online_chapter = latest_online_chapter
                story.online_chapters = online_chapters or 0

    # ── deletes ───────────────────────────────────────────────────────────

    def delete(self, story_id: int) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                db.delete(story)

    def delete_with_relations(self, story_id: int) -> None:
        # FK cascades handle everything — just delete the story.
        # PRAGMA foreign_keys=ON is set in engine.py.
        self.delete(story_id)


# ── helper ────────────────────────────────────────────────────────────────

def _to_dict(story: Story | None) -> dict | None:
    if story is None:
        return None
    return {
        "id":                        story.id,
        "title":                     story.title,
        "author":                    story.author,
        "source_url":                story.source_url,
        "local_path":                story.local_path,
        "cover_path":                story.cover_path,
        "total_chapters":            story.total_chapters,
        "downloaded_chapters":       story.downloaded_chapters,
        "latest_online_chapter":     story.latest_online_chapter,
        "latest_downloaded_chapter": story.latest_downloaded_chapter,
        "online_chapters":           story.online_chapters,
        "last_updated":              story.last_updated,
        "created_at":                story.created_at,
    }
