# novelcast/db/repositories/author_repository.py

import re

from sqlalchemy import func, select

from novelcast.db.models.author import Author
from novelcast.db.models.author_link import AuthorLink
from novelcast.db.models.relationships import story_author
from novelcast.db.models.story import Story
from novelcast.db.repositories.base import BaseRepository


class AuthorRepository(BaseRepository):
    # ── reads ──────────────────────────────────────────────────────────────

    def get_all_with_stats(self) -> list[dict]:
        """All authors with story_count, last_updated, first_story_at."""
        with self.session_no_commit() as db:
            stats_sq = (
                select(
                    story_author.c.author_id.label("author_id"),
                    func.count(story_author.c.story_id).label("story_count"),
                    func.max(Story.last_updated).label("last_updated"),
                    func.min(Story.created_at).label("first_story_at"),
                )
                .join(Story, Story.id == story_author.c.story_id)
                .group_by(story_author.c.author_id)
                .subquery()
            )

            rows = db.execute(
                select(Author, stats_sq).outerjoin(stats_sq, stats_sq.c.author_id == Author.id).order_by(Author.name)
            ).all()

            result = []
            for row in rows:
                author = row[0]
                result.append(
                    {
                        "id": author.id,
                        "name": author.name,
                        "bio": author.bio,
                        "picture_path": author.picture_path,
                        "links": [_link_to_dict(lnk) for lnk in author.links],
                        "story_count": row.story_count or 0,
                        "last_updated": row.last_updated,
                        "first_story_at": row.first_story_at,
                    }
                )
            return result

    def get_by_id(self, author_id: int) -> dict | None:
        with self.session_no_commit() as db:
            author = db.get(Author, author_id)
            if not author:
                return None

            stories = db.scalars(
                select(Story)
                .join(story_author, story_author.c.story_id == Story.id)
                .where(story_author.c.author_id == author_id)
                .order_by(Story.title)
            ).all()

            return {
                "id": author.id,
                "name": author.name,
                "bio": author.bio,
                "picture_path": author.picture_path,
                "links": [_link_to_dict(lnk) for lnk in author.links],
                "stories": [_story_to_dict(s) for s in stories],
            }

    def get_for_story(self, story_id: int) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(Author)
                .join(story_author, story_author.c.author_id == Author.id)
                .where(story_author.c.story_id == story_id)
                .order_by(Author.name)
            ).all()
            return [_author_to_dict(a) for a in rows]

    def find_collision(self, name: str, exclude_id: int | None = None) -> dict | None:
        """Return an existing author whose normalized name matches `name`, if any."""
        target = _normalize_author_name(name)
        with self.session_no_commit() as db:
            for a in db.scalars(select(Author)).all():
                if exclude_id is not None and a.id == exclude_id:
                    continue
                if _normalize_author_name(a.name) == target:
                    return _author_to_dict(a)
        return None

    def find_duplicate_groups(self) -> list[list[dict]]:
        """Group all authors by normalized name; return only groups with 2+ members."""
        with self.session_no_commit() as db:
            authors = db.scalars(select(Author)).all()
        groups: dict[str, list[dict]] = {}
        for a in authors:
            key = _normalize_author_name(a.name)
            groups.setdefault(key, []).append(_author_to_dict(a))
        return [g for g in groups.values() if len(g) > 1]

    # ── writes ─────────────────────────────────────────────────────────────

    def get_or_create(self, name: str) -> int:
        """Match on normalized name so scrapers/downloads don't spawn near-duplicate authors."""
        target = _normalize_author_name(name)
        with self.session() as db:
            for a in db.scalars(select(Author)).all():
                if _normalize_author_name(a.name) == target:
                    return a.id
            author = Author(name=name)
            db.add(author)
            db.flush()
            return author.id

    def update(
        self,
        author_id: int,
        name: str,
        bio: str | None = None,
        picture_path: str | None = None,
        force: bool = False,
    ) -> dict | None:
        """
        Update an author's name/bio/picture.

        If `force` is False and another author already has the same normalized
        name, no write happens — instead the dict is returned in the shape
        {"conflict": <other author dict>} so the caller can prompt to merge.
        Pass force=True to rename anyway (creating a same-name duplicate on
        purpose), or call merge() to fold the two together instead.
        """
        with self.session() as db:
            author = db.get(Author, author_id)
            if not author:
                return None

            if not force:
                target = _normalize_author_name(name)
                for a in db.scalars(select(Author)).all():
                    if a.id != author_id and _normalize_author_name(a.name) == target:
                        return {"conflict": _author_to_dict(a)}

            author.name = name
            author.bio = bio
            author.picture_path = picture_path
            db.flush()
            return _author_to_dict(author)

    def merge(self, primary_id: int, duplicate_ids: list[int]) -> dict | None:
        """
        Fold one or more duplicate authors into `primary_id`:
        - reassigns all story links from duplicates to the primary (skipping
          links the primary already has)
        - fills primary.bio / primary.picture_path from a duplicate if the
          primary doesn't have one set
        - merges links, de-duping by URL
        - deletes the duplicate author rows
        """
        with self.session() as db:
            primary = db.get(Author, primary_id)
            if not primary:
                return None

            for dup_id in duplicate_ids:
                if dup_id == primary_id:
                    continue
                dup = db.get(Author, dup_id)
                if not dup:
                    continue

                story_ids = db.scalars(
                    select(story_author.c.story_id).where(story_author.c.author_id == dup_id)
                ).all()
                for story_id in story_ids:
                    exists = db.execute(
                        story_author.select().where(
                            story_author.c.author_id == primary_id,
                            story_author.c.story_id == story_id,
                        )
                    ).first()
                    if not exists:
                        db.execute(story_author.insert().values(author_id=primary_id, story_id=story_id))
                db.execute(story_author.delete().where(story_author.c.author_id == dup_id))

                if not primary.bio and dup.bio:
                    primary.bio = dup.bio
                if not primary.picture_path and dup.picture_path:
                    primary.picture_path = dup.picture_path

                existing_urls = {lnk.url for lnk in primary.links}
                for lnk in list(dup.links):
                    if lnk.url in existing_urls:
                        db.delete(lnk)
                    else:
                        lnk.author_id = primary_id
                        existing_urls.add(lnk.url)

                db.delete(dup)

            db.flush()
            return _author_to_dict(primary)

    def link_to_story(self, author_id: int, story_id: int) -> None:
        with self.session() as db:
            exists = db.execute(
                story_author.select().where(
                    story_author.c.author_id == author_id,
                    story_author.c.story_id == story_id,
                )
            ).first()
            if not exists:
                db.execute(story_author.insert().values(author_id=author_id, story_id=story_id))

    def unlink_from_story(self, author_id: int, story_id: int) -> None:
        with self.session() as db:
            db.execute(
                story_author.delete().where(
                    story_author.c.author_id == author_id,
                    story_author.c.story_id == story_id,
                )
            )

    def set_links(self, author_id: int, links: list[dict]) -> list[dict]:
        with self.session() as db:
            db.execute(AuthorLink.__table__.delete().where(AuthorLink.author_id == author_id))
            saved = []
            for item in links:
                label = (item.get("label") or "").strip()
                url = (item.get("url") or "").strip()
                if not label or not url:
                    continue
                link = AuthorLink(author_id=author_id, label=label, url=url)
                db.add(link)
                db.flush()
                saved.append(_link_to_dict(link))
            return saved


# ── helpers ────────────────────────────────────────────────────────────────


def _normalize_author_name(name: str) -> str:
    """'Brian J. Nordon' and 'Brian J Nordon' both fold to 'brian j nordon'."""
    name = name.strip().lower()
    name = re.sub(r"\.", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _author_to_dict(author: Author | None) -> dict | None:
    if author is None:
        return None
    return {
        "id": author.id,
        "name": author.name,
        "bio": author.bio,
        "picture_path": author.picture_path,
        "links": [_link_to_dict(lnk) for lnk in author.links],
    }


def _link_to_dict(link: AuthorLink) -> dict:
    return {"id": link.id, "label": link.label, "url": link.url}


def _story_to_dict(story: Story) -> dict:
    return {
        "id": story.id,
        "title": story.title,
        "cover_path": story.cover_path,
        "downloaded_chapters": story.downloaded_chapters,
        "total_chapters": story.total_chapters,
        "last_updated": story.last_updated,
    }