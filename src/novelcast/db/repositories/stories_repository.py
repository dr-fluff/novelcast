# novelcast/db/repositories/stories_repository.py

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.story import Story
from novelcast.db.models.chapter import Chapter, ChapterFile
from novelcast.db.models.tag import Tag
from novelcast.db.models.genre import Genre
from novelcast.db.models.series import Series
from novelcast.db.models.settings import StorySetting
from novelcast.utils.files import human_readable_size


class StoriesRepository(BaseRepository):

    # ── reads ──────────────────────────────────────────────────────────────

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
            rows = db.execute(
                select(ChapterFile.file_path)
                .join(Chapter, Chapter.id == ChapterFile.chapter_id)
                .where(
                    Chapter.story_id == story_id,
                    ChapterFile.file_path.isnot(None),
                    ChapterFile.file_path != "",
                )
            ).all()
            return [row[0] for row in rows]

    def get_chapter_numbers(self, story_id: int) -> list[int]:
        with self.session_no_commit() as db:
            return list(db.scalars(
                select(Chapter.chapter_number).where(Chapter.story_id == story_id)
            ).all())

    # ── writes ─────────────────────────────────────────────────────────────

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

    def update_full_metadata(
        self,
        story_id: int,
        title: str,
        author: str | None,
        subtitle: str | None = None,
        description: str | None = None,
        publish_year: int | None = None,
        language: str | None = None,
        series: list[str] | None = None,
        genres: list[str] | None = None,
        tags: list[str] | None = None,
        source_url: str | None = None,
        auto_update: bool | None = None,  # ← ADD THIS
    ) -> dict | None:
        """Used by the metadata edit panel."""
        with self.session() as db:
            story = db.get(Story, story_id)
            if not story:
                return None
            story.title = title
            story.author = author
            story.subtitle = subtitle
            story.description = description
            story.publish_year = publish_year
            story.language = language
            if source_url is not None:
                story.source_url = source_url
            
            # ← ADD THIS BLOCK
            if auto_update is not None:
                self.set_story_setting(
                    story_id,
                    "auto_update",
                    "1" if auto_update else "0",
                )
            
            _sync_story_relations(db, story, Series, "series", series or [])
            _sync_story_relations(db, story, Genre, "genres", genres or [])
            _sync_story_relations(db, story, Tag, "tags", tags or [])
            story.last_updated = datetime.now(timezone.utc)
            db.flush()
            return _to_dict(story)

    def update_paths(self, story_id: int, local_path: str, cover_path: str | None = None) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                story.local_path = local_path
                story.cover_path = cover_path

    def set_story_setting(self, story_id: int, name: str, value: str, category: str | None = None, type: str = "str") -> None:
        """Create or update a StorySetting entry for a story."""
        with self.session() as db:
            existing = db.scalars(
                select(StorySetting).where(StorySetting.story_id == story_id, StorySetting.name == name)
            ).first()
            if existing:
                existing.value = value
                existing.category = category
                existing.type = type
            else:
                s = StorySetting(story_id=story_id, name=name, value=value, category=category, type=type)
                db.add(s)

    def get_story_setting(self, story_id: int, name: str) -> str | None:
        with self.session_no_commit() as db:
            s = db.scalars(
                select(StorySetting).where(StorySetting.story_id == story_id, StorySetting.name == name)
            ).first()
            return s.value if s else None

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

    # ── deletes ────────────────────────────────────────────────────────────

    def delete(self, story_id: int) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                db.delete(story)

    def delete_with_relations(self, story_id: int) -> None:
        self.delete(story_id)


def _sync_story_relations(db, story, model, attr_name, names):
    normalized = []
    for name in names:
        if not name:
            continue
        value = str(name).strip()
        if not value:
            continue
        existing = next((item for item in getattr(story, attr_name) if item.name == value), None)
        if existing:
            normalized.append(existing)
            continue
        item = db.scalars(select(model).where(model.name == value)).first()
        if item is None:
            item = model(name=value)
            db.add(item)
            db.flush()
        normalized.append(item)
    getattr(story, attr_name).clear()
    getattr(story, attr_name).extend(normalized)


# ── helper ─────────────────────────────────────────────────────────────────

def _to_dict(story: Story | None) -> dict | None:
    if story is None:
        return None
    return {
        "id":                        story.id,
        "title":                     story.title,
        "author":                    story.author,
        "subtitle":                  getattr(story, "subtitle", None),
        "source_url":                story.source_url,
        "auto_update":               any(
            str(s.value).lower() in ("1", "true", "yes")
            for s in getattr(story, "settings", []) or []
            if s.name == "auto_update"
        ),
        "local_path":                story.local_path,
        "cover_path":                story.cover_path,
        "total_chapters":            story.total_chapters,
        "downloaded_chapters":       story.downloaded_chapters,
        "latest_online_chapter":     story.latest_online_chapter,
        "latest_downloaded_chapter": story.latest_downloaded_chapter,
        "online_chapters":           story.online_chapters,
        "last_updated":              story.last_updated,
        "description":               getattr(story, "description", None),
        "publish_year":              getattr(story, "publish_year", None),
        "language":                  getattr(story, "language", None),
        "publisher":                 getattr(story, "publisher", None),
        "narrators":                 getattr(story, "narrators", None),
        # normalized relations: join names into readable strings
        "genres":                    ", ".join([g.name for g in getattr(story, "genres", [])]) if getattr(story, "genres", None) else None,
        "tags":                      ", ".join([t.name for t in getattr(story, "tags", [])]) if getattr(story, "tags", None) else None,
        "series":                    ", ".join([s.name for s in getattr(story, "series", [])]) if getattr(story, "series", None) else None,
        "genres_list":              [g.name for g in getattr(story, "genres", [])],
        "tags_list":                [t.name for t in getattr(story, "tags", [])],
        "series_list":              [s.name for s in getattr(story, "series", [])],
        "duration":                  getattr(story, "duration", None),
        "size":                      None,
        "created_at":                story.created_at,
    }

    # try to read computed size from model field or story settings
    try:
        size_field = getattr(story, "size", None)
        if size_field:
            result = dict(result)
            result["size"] = human_readable_size(int(size_field))
            return result

        # check settings relationship for stored computed.size
        settings = getattr(story, "settings", []) or []
        for s in settings:
            if s.name == "computed.size":
                try:
                    bytes_val = int(s.value)
                    result = dict(result)
                    result["size"] = human_readable_size(bytes_val)
                    return result
                except Exception:
                    break
    except Exception:
        pass

    return result
