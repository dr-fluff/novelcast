"""
novelcast/db/models/relationships.py

Pure association tables (no extra columns — those become full models).
Import this module in init_db.py so SQLAlchemy registers the tables.
"""

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
