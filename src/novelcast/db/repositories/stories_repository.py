# novelcast/db/repositories/stories_repository.py

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.models import (
    Chapter,
    ChapterFile,
    Genre,
    Series,
    Story,
    StorySetting,
    Tag,
)
from novelcast.db.repositories.base import BaseRepository
from novelcast.utils.files import human_readable_size


class StoriesRepository(BaseRepository):
    # ── reads ──────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        with self.session_no_commit() as db:
            stories = db.scalars(select(Story).order_by(Story.created_at.desc())).all()
            dicts = [_to_dict(s) for s in stories]

            # One query: latest chapter title per story
            subq = (
                select(
                    Chapter.story_id,
                    func.max(Chapter.chapter_number).label("max_num"),
                )
                .group_by(Chapter.story_id)
                .subquery()
            )
            rows = db.execute(
                select(Chapter.story_id, Chapter.title).join(
                    subq,
                    (Chapter.story_id == subq.c.story_id) & (Chapter.chapter_number == subq.c.max_num),
                )
            ).all()
            latest_title = {row.story_id: row.title for row in rows}

            for d in dicts:
                d["chapter"] = latest_title.get(d["id"])

            return dicts

    def get_by_id(self, story_id: int) -> dict | None:
        with self.session_no_commit() as db:
            return _to_dict(db.get(Story, story_id))

    def get_by_url(self, url: str) -> dict | None:
        with self.session_no_commit() as db:
            story = db.scalars(select(Story).where(Story.source_url == url)).first()
            return _to_dict(story)

    def get_story_site_id(self, story_id: int) -> str:
        pass

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
            return list(db.scalars(select(Chapter.chapter_number).where(Chapter.story_id == story_id)).all())

    def get_stories_by_site(self, site: str) -> list[dict]:
        with self.session_no_commit() as db:
            stories = db.scalars(
                select(Story)
                .where(Story.site == site)
                .where(Story.story_site_id.isnot(None))
                .where(Story.story_site_id != "")
            ).all()

            return [_to_dict(s) for s in stories]

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
        auto_update: bool | None = None,
        hide_author_notes: bool | None = None,
        story_site_id: str | None = None,
    ) -> dict | None:
        """Used by the metadata edit panel."""
        with self.session() as db:
            story = db.get(Story, story_id)  # FIX: was `id` (Python builtin)
            if not story:
                return None
            story.title = title
            # FIX: removed bogus `story.story_id = story_id` — Story has no such column
            story.author = author
            story.subtitle = subtitle
            story.description = description
            story.publish_year = publish_year
            story.language = language
            if source_url is not None:
                story.source_url = source_url
            if story_site_id is not None:
                story.story_site_id = story_site_id

            if auto_update is not None:
                self.set_story_setting(
                    story_id,
                    "auto_update",
                    "1" if auto_update else "0",
                )
            if hide_author_notes is not None:
                self.set_story_setting(
                    story_id,
                    "hide_author_notes",
                    "1" if hide_author_notes else "0",
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

    def set_story_setting(
        self,
        story_id: int,
        name: str,
        value: str,
        category: str | None = None,
        type: str = "str",
    ) -> None:
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
                s = StorySetting(
                    story_id=story_id,
                    name=name,
                    value=value,
                    category=category,
                    type=type,
                )
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

    result = {
        "id": story.id,
        "title": story.title,
        "author": story.author,
        "subtitle": getattr(story, "subtitle", None),
        "source_url": story.source_url,
        "story_site_id": story.story_site_id,
        "auto_update": _story_setting_bool(story, "auto_update", default=False),
        "hide_author_notes": _story_setting_bool(story, "hide_author_notes", default=True),
        "local_path": story.local_path,
        "cover_path": story.cover_path,
        "total_chapters": story.total_chapters,
        "downloaded_chapters": story.downloaded_chapters,
        "latest_online_chapter": story.latest_online_chapter,
        "latest_downloaded_chapter": story.latest_downloaded_chapter,
        "online_chapters": story.online_chapters,
        "last_updated": story.last_updated,
        "description": getattr(story, "description", None),
        "publish_year": getattr(story, "publish_year", None),
        "language": getattr(story, "language", None),
        "publisher": getattr(story, "publisher", None),
        "narrators": getattr(story, "narrators", None),
        "genres": ", ".join([g.name for g in getattr(story, "genres", [])]) if getattr(story, "genres", None) else None,
        "tags": ", ".join([t.name for t in getattr(story, "tags", [])]) if getattr(story, "tags", None) else None,
        "series": ", ".join([s.name for s in getattr(story, "series", [])]) if getattr(story, "series", None) else None,
        "genres_list": [g.name for g in getattr(story, "genres", [])],
        "tags_list": [t.name for t in getattr(story, "tags", [])],
        "series_list": [s.name for s in getattr(story, "series", [])],
        "duration": getattr(story, "duration", None),
        "size": None,
        "created_at": story.created_at,
    }

    # FIX: size enrichment was unreachable (came after an early return). Now runs correctly.
    try:
        size_field = getattr(story, "size", None)
        if size_field:
            result["size"] = human_readable_size(int(size_field))
            return result

        settings = getattr(story, "settings", []) or []
        for s in settings:
            if s.name == "computed.size":
                try:
                    result["size"] = human_readable_size(int(s.value))
                except Exception:
                    pass
                break
    except Exception:
        pass

    return result


def _story_setting_bool(story: Story, name: str, default: bool = False) -> bool:
    for setting in getattr(story, "settings", []) or []:
        if setting.name == name:
            return str(setting.value).lower() in ("1", "true", "yes")
    return default
