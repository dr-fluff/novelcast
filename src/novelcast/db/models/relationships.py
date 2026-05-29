# novelcast/db/models/relationships.py


from sqlalchemy import Column, ForeignKey, Table

from novelcast.db.base import Base


# Many-to-many: stories ↔ authors
story_author = Table(
    "story_author",
    Base.metadata,
    Column("story_id", ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-many: users ↔ groups
user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)

story_tags = Table(
    "story_tags",
    Base.metadata,
    Column("story_id", ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

story_genres = Table(
    "story_genres",
    Base.metadata,
    Column("story_id", ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

story_series = Table(
    "story_series",
    Base.metadata,
    Column("story_id", ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True),
    Column("series_id", ForeignKey("series.id", ondelete="CASCADE"), primary_key=True),
)