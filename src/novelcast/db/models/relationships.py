# novelcast/db/models/relationships.py

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from novelcast.db.base import Base


class StoryAuthor(Base):
    __tablename__ = "story_author"

    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)


class UserGroup(Base):
    __tablename__ = "user_groups"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)


class StoryTag(Base):
    __tablename__ = "story_tags"

    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class StoryGenre(Base):
    __tablename__ = "story_genres"

    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


class StorySeries(Base):
    __tablename__ = "story_series"

    story_id: Mapped[int] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), primary_key=True)


# Preserve the public names used by the existing relationship declarations.
story_author = StoryAuthor.__table__
user_groups = UserGroup.__table__
story_tags = StoryTag.__table__
story_genres = StoryGenre.__table__
story_series = StorySeries.__table__
