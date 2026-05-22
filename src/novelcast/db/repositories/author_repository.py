# novelcast/db/repositories/author_repository.py

from sqlalchemy import select, func

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.author import Author
from novelcast.db.models.author_link import AuthorLink
from novelcast.db.models.story import Story
from novelcast.db.models.relationships import story_author


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
                select(Author, stats_sq)
                .outerjoin(stats_sq, stats_sq.c.author_id == Author.id)
                .order_by(Author.name)
            ).all()

            result = []
            for row in rows:
                author = row[0]
                result.append({
                    "id":             author.id,
                    "name":           author.name,
                    "bio":            author.bio,
                    "picture_path":   author.picture_path,
                    "links":          [_link_to_dict(lnk) for lnk in author.links],
                    "story_count":    row.story_count    or 0,
                    "last_updated":   row.last_updated,
                    "first_story_at": row.first_story_at,
                })
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
                "id":           author.id,
                "name":         author.name,
                "bio":          author.bio,
                "picture_path": author.picture_path,
                "links":        [_link_to_dict(lnk) for lnk in author.links],
                "stories":      [_story_to_dict(s) for s in stories],
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

    # ── writes ─────────────────────────────────────────────────────────────

    def get_or_create(self, name: str) -> int:
        with self.session() as db:
            author = db.scalars(select(Author).where(Author.name == name)).first()
            if author is None:
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
    ) -> dict | None:
        with self.session() as db:
            author = db.get(Author, author_id)
            if not author:
                return None
            author.name         = name
            author.bio          = bio
            author.picture_path = picture_path
            db.flush()
            return _author_to_dict(author)

    def link_to_story(self, author_id: int, story_id: int) -> None:
        with self.session() as db:
            exists = db.execute(
                story_author.select().where(
                    story_author.c.author_id == author_id,
                    story_author.c.story_id  == story_id,
                )
            ).first()
            if not exists:
                db.execute(
                    story_author.insert().values(author_id=author_id, story_id=story_id)
                )

    def unlink_from_story(self, author_id: int, story_id: int) -> None:
        with self.session() as db:
            db.execute(
                story_author.delete().where(
                    story_author.c.author_id == author_id,
                    story_author.c.story_id  == story_id,
                )
            )

    def set_links(self, author_id: int, links: list[dict]) -> list[dict]:
        with self.session() as db:
            db.execute(
                AuthorLink.__table__.delete().where(AuthorLink.author_id == author_id)
            )
            saved = []
            for item in links:
                label = (item.get("label") or "").strip()
                url   = (item.get("url")   or "").strip()
                if not label or not url:
                    continue
                link = AuthorLink(author_id=author_id, label=label, url=url)
                db.add(link)
                db.flush()
                saved.append(_link_to_dict(link))
            return saved


# ── helpers ────────────────────────────────────────────────────────────────

def _author_to_dict(author: Author | None) -> dict | None:
    if author is None:
        return None
    return {
        "id":           author.id,
        "name":         author.name,
        "bio":          author.bio,
        "picture_path": author.picture_path,
        "links":        [_link_to_dict(lnk) for lnk in author.links],
    }


def _link_to_dict(link: AuthorLink) -> dict:
    return {"id": link.id, "label": link.label, "url": link.url}


def _story_to_dict(story: Story) -> dict:
    return {
        "id":                  story.id,
        "title":               story.title,
        "cover_path":          story.cover_path,
        "downloaded_chapters": story.downloaded_chapters,
        "total_chapters":      story.total_chapters,
        "last_updated":        story.last_updated,
    }
