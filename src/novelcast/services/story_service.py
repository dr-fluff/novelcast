# novelcast/services/story_service.py

from pathlib import Path
from urllib.parse import quote
import re

from novelcast.db.repositories.author_repository import AuthorRepository


class StoryService:
    def __init__(self, repo, author_repo: AuthorRepository | None = None):
        self.repo        = repo
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

    def get_by_url(self, url: str):
        return self.repo.get_by_url(url)

    # ── story writes ───────────────────────────────────────────────────────

    def create_story(self, title, author=None, url=None):
        return self.repo.create(title, author, url)

    def delete_story(self, story_id: int):
        story = self.get_story(story_id)
        if not story:
            return False

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
        return updated

    # ── author reads ───────────────────────────────────────────────────────

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
