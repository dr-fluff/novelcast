# novelcast/services/story_service.py

import logging
import re
from pathlib import Path
from urllib.parse import quote

from novelcast.db.models import Story
from novelcast.db.repositories import AuthorRepository
from novelcast.utils.url import get_site_from_url

logger = logging.getLogger(__name__)


class StoryService:
    def __init__(self, repo, author_repo: AuthorRepository | None = None):
        self.repo = repo
        self.author_repo = author_repo

    # ── path helper ────────────────────────────────────────────────────────

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if path.is_absolute():
            return path
        candidate = Path.cwd() / path
        if candidate.exists():
            return candidate
        project_root = Path(__file__).resolve().parents[3]
        candidate = project_root / path
        if candidate.exists():
            return candidate
        return path

    def _cover_url(self, cover_path: str | None) -> str | None:
        if not cover_path:
            return None
        if cover_path.startswith(("http://", "https://", "/static/")):
            return cover_path
        return f"/covers?path={quote(cover_path)}"

    def _parse_comma_separated(self, raw: str | None) -> list[str]:
        if not raw:
            return []
        return [item.strip() for item in re.split(r"[;,]", raw) if item.strip()]

    def _sync_story_authors(self, story_id: int, author_names: list[str]) -> None:
        if not self.author_repo:
            return

        existing = self.author_repo.get_for_story(story_id)
        requested = [name for name in author_names if name]

        for name in requested:
            author_id = self.author_repo.get_or_create(name)
            self.author_repo.link_to_story(author_id, story_id)

        for existing_author in existing:
            if existing_author["name"] not in requested:
                self.author_repo.unlink_from_story(existing_author["id"], story_id)

    # ── story reads ────────────────────────────────────────────────────────

    def get_all_stories(self):
        return self.repo.get_all()

    def get_story(self, story_id: int):
        data = self.repo.get_by_id(story_id)
        if not data:
            return None

        # resolve cover URL for templates
        data["cover_url"] = self._cover_url(data.get("cover_path"))
        return data

    def get_story_files(self, story_id: int) -> list[dict]:
        story = self.get_story(story_id)
        if not story:
            return []

        local_path = story.get("local_path")
        if not local_path:
            return []

        path = self._resolve_path(local_path)
        if not path.exists() or not path.is_dir():
            return []

        from novelcast.utils.files import human_readable_size

        files: list[dict] = []
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            stat = file_path.stat()
            files.append(
                {
                    "name": file_path.name,
                    "relative_path": str(file_path.relative_to(path)),
                    "path": str(file_path),
                    "size": human_readable_size(stat.st_size),
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                }
            )

        return files

    def get_by_url(self, url: str):
        return self.repo.get_by_url(url)

    # ── story writes ───────────────────────────────────────────────────────

    def create_story(self, title, author=None, url=None):
        return self.repo.create(title, author, url)

    def delete_story(self, story_id: int):
        story = self.get_story(story_id)
        if not story:
            return False

        title = story.get("title") or "Unknown"

        local_path = story.get("local_path")
        if local_path:
            path = self._resolve_path(local_path)
            if path.is_dir():
                import shutil

                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()

        for file_path in self.repo.get_chapter_file_paths(story_id):
            path = self._resolve_path(file_path)
            if path.exists():
                path.unlink()

        cover_path = story.get("cover_path")
        if cover_path and not cover_path.startswith(("http://", "https://", "/static/")):
            cover_file = self._resolve_path(cover_path)
            if cover_file.exists():
                cover_file.unlink()

        self.repo.delete_with_relations(story_id)

        telegram = getattr(self, "telegram", None)
        if telegram:
            telegram.notify_story_deleted(title)

        return True

    def update_story_metadata(
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
        hide_author_notes: bool | None = None,  # ← ADD
    ) -> dict | None:
        updated = self.repo.update_full_metadata(
            story_id=story_id,
            title=title,
            author=author,
            subtitle=subtitle,
            description=description,
            publish_year=publish_year,
            language=language,
            series=series,
            genres=genres,
            tags=tags,
            source_url=source_url,
        )
        if updated and self.author_repo and author is not None:
            names = self._parse_comma_separated(author)
            self._sync_story_authors(story_id, names)
        if updated and auto_update is not None:
            self.repo.set_story_setting(
                story_id,
                "auto_update",
                "1" if bool(auto_update) else "0",
                category="story",
                type="bool",
            )
        if updated and hide_author_notes is not None:  # ← ADD
            self.repo.set_story_setting(
                story_id,
                "hide_author_notes",
                "1" if bool(hide_author_notes) else "0",
                category="story",
                type="bool",
            )
        return updated

    # ── author reads ───────────────────────────────────────────────────────

    def get_stories_by_site(self, site: str) -> list[dict]:
        stories = self.repo.get_all()

        return [story for story in stories if get_site_from_url(story.get("source_url")) == site]

    def get_auto_update_stories_by_site(self, site: str) -> list[dict]:
        """Same as get_stories_by_site, but restricted to stories with the
        auto_update story setting enabled. Used by RSS readers so stories
        the user hasn't opted into auto-updating aren't polled/downloaded."""
        return [story for story in self.get_stories_by_site(site) if story.get("auto_update")]

    def get_story_by_site_id(self, site: str, site_id: str | None) -> dict | None:
        """Find a story by its external site + site_id (e.g. RoyalRoad's
        numeric fiction id), matching Story.story_site_id."""
        if not site_id:
            return None

        for story in self.get_stories_by_site(site):
            if str(story.get("story_site_id")) == str(site_id):
                return story

        return None

    def get_all_authors(self, query: str = "", sort: str = "name") -> list[dict]:
        if not self.author_repo:
            return []

        authors = self.author_repo.get_all_with_stats()

        if query:
            q = query.lower()
            authors = [a for a in authors if q in a["name"].lower()]

        if sort == "stories":
            authors = sorted(authors, key=lambda a: a["story_count"], reverse=True)
        elif sort == "updated":
            authors = sorted(authors, key=lambda a: a["last_updated"] or "", reverse=True)
        elif sort == "added":
            authors = sorted(authors, key=lambda a: a["first_story_at"] or "", reverse=True)
        else:
            authors = sorted(authors, key=lambda a: a["name"].lower())

        # resolve picture URLs
        for a in authors:
            a["picture_url"] = self._cover_url(a.get("picture_path"))

        return authors

    def get_author(self, author_id: int) -> dict | None:
        if not self.author_repo:
            return None
        data = self.author_repo.get_by_id(author_id)
        if not data:
            return None

        data["picture_url"] = self._cover_url(data.get("picture_path"))

        for s in data.get("stories", []):
            s["cover_url"] = self._cover_url(s.get("cover_path"))

        return data

    def get_story_authors(self, story_id: int) -> list[dict]:
        if not self.author_repo:
            return []
        return self.author_repo.get_for_story(story_id)

    # ── author writes ──────────────────────────────────────────────────────

    def update_author(self, author_id: int, name: str, bio: str | None = None) -> dict | None:
        if not self.author_repo:
            return None
        return self.author_repo.update(author_id, name, bio)

    def set_author_links(self, author_id: int, links: list[dict]) -> list[dict]:
        if not self.author_repo:
            return []
        return self.author_repo.set_links(author_id, links)

    # In novelcast/repositories/story_repository.py

    def count_pending_syncs(self) -> int:

        from sqlalchemy import func

        return (
            self._db.query(func.count(Story.id))
            .filter(Story.sync_status == "pending")  # adjust field/value
            .scalar()
            or 0
        )
