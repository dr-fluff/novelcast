import json
import re
from datetime import UTC, datetime
from pathlib import Path

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

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str | None:
    """Defensive cleanup for any field that could end up holding rendered
    markup (e.g. an edit form accidentally round-tripping the index page's
    filter-link HTML back through save). Plain strings pass through untouched."""
    if not value:
        return value
    return _HTML_TAG_RE.sub("", value).strip()


class StoriesRepository(BaseRepository):
    # ── reads ──────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        with self.session_no_commit() as db:
            stories = db.scalars(select(Story).order_by(Story.created_at.desc())).all()
            dicts = [_to_dict(s) for s in stories]

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

    def get_existing_local_paths(self, exclude_story_id: int | None = None) -> set[str]:
        with self.session_no_commit() as db:
            query = select(Story.local_path).where(Story.local_path.isnot(None))
            if exclude_story_id is not None:
                query = query.where(Story.id != exclude_story_id)
            rows = db.execute(query).all()
            return {row[0] for row in rows if row[0]}

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
                        "last_updated": datetime.now(UTC),
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
                story.last_updated = datetime.now(UTC)

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
        is_user_edit: bool = False,
    ) -> dict | None:
        """
        Two callers, two behaviors:

        - GUI edit/add panel (is_user_edit=True): applies every field the
          user submitted, and records which fields actually *changed* vs
          the current DB value in `locked_fields`.
        - Scrape/sync pipeline (is_user_edit=False, the default — used by
          StoryDownloadService._update_story_metadata): applies freshly
          scraped values EXCEPT for any field name already present in
          `locked_fields`, so a manual edit is never silently overwritten
          by the next auto-update.

        Cover is intentionally not tracked here — it's written separately
        by StoryPipeline.persist()/update_paths() and always refreshes.
        """
        with self.session() as db:
            story = db.get(Story, story_id)
            if not story:
                return None

            locked = set(json.loads(story.locked_fields)) if story.locked_fields else set()

            def apply_scalar(field: str, new_value, sanitize: bool = False):
                if sanitize and isinstance(new_value, str):
                    new_value = _strip_html(new_value)
                if is_user_edit:
                    old_value = getattr(story, field)
                    setattr(story, field, new_value)
                    if new_value != old_value:
                        locked.add(field)
                else:
                    if field not in locked:
                        setattr(story, field, new_value)

            apply_scalar("title", title, sanitize=True)
            apply_scalar("author", author, sanitize=True)
            apply_scalar("subtitle", subtitle, sanitize=True)
            apply_scalar("description", description)
            apply_scalar("publish_year", publish_year)
            apply_scalar("language", language)

            if source_url is not None:
                story.source_url = source_url
            if story_site_id is not None:
                story.story_site_id = story_site_id

            if auto_update is not None:
                self.set_story_setting(story_id, "auto_update", "1" if auto_update else "0")
            if hide_author_notes is not None:
                self.set_story_setting(story_id, "hide_author_notes", "1" if hide_author_notes else "0")

            def apply_relation(field: str, model, raw_names: list[str] | None):
                cleaned = [n for n in (_strip_html(v) for v in (raw_names or [])) if n]
                if is_user_edit:
                    old_names = sorted(item.name for item in getattr(story, field))
                    _sync_story_relations(db, story, model, field, cleaned)
                    if sorted(cleaned) != old_names:
                        locked.add(field)
                else:
                    if field not in locked:
                        _sync_story_relations(db, story, model, field, cleaned)

            apply_relation("series", Series, series)
            apply_relation("genres", Genre, genres)
            apply_relation("tags", Tag, tags)

            story.locked_fields = json.dumps(sorted(locked)) if locked else None
            story.last_updated = datetime.now(UTC)
            db.flush()
            return _to_dict(story)

    def update_paths(self, story_id: int, local_path: str, cover_path: str | None = None) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                desired_local_path = local_path
                if desired_local_path:
                    conflict_id = db.scalar(
                        select(Story.id).where(Story.local_path == desired_local_path, Story.id != story_id)
                    )
                    if conflict_id is not None:
                        base_path = Path(desired_local_path)
                        parent = base_path.parent
                        suffix = 2
                        candidate = base_path
                        while db.scalar(select(Story.id).where(Story.local_path == str(candidate), Story.id != story_id)) is not None:
                            candidate = parent / f"{base_path.name}_{suffix}"
                            suffix += 1
                        desired_local_path = str(candidate)
                        candidate.mkdir(parents=True, exist_ok=True)

                story.local_path = desired_local_path
                if cover_path is not None and story.cover_path is None:
                    story.cover_path = cover_path

    def update_cover(self, story_id: int, cover_path: str | None) -> None:
        with self.session() as db:
            story = db.get(Story, story_id)
            if story:
                story.cover_path = cover_path

    def restore_local_cover_paths(self) -> int:
        restored = 0
        with self.session() as db:
            stories = db.scalars(select(Story).where(Story.cover_path.is_(None))).all()
            for story in stories:
                if not story.local_path:
                    continue
                cover_path = Path(story.local_path) / "cover.jpg"
                if cover_path.is_file():
                    story.cover_path = str(cover_path)
                    restored += 1
        return restored

    def set_story_setting(
        self,
        story_id: int,
        name: str,
        value: str,
        category: str | None = None,
        type: str = "str",
    ) -> None:
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
        "locked_fields": json.loads(story.locked_fields) if getattr(story, "locked_fields", None) else [],
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
