from sqlalchemy import Table, Column, ForeignKey
from .base import Base

story_author = Table(
    "story_author",
    Base.metadata,
    Column("story_id", ForeignKey("stories.id"), primary_key=True),
    Column("author_id", ForeignKey("authors.id"), primary_key=True),
)

user_groups = Table(
    "user_groups",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("group_id", ForeignKey("groups.id"), primary_key=True),
)