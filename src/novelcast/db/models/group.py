# novelcast/db/models/group.py

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.story import Story
    from novelcast.db.models.user import User


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    members: Mapped[list["User"]] = relationship("User", secondary="user_groups", back_populates="groups")
    story_permissions: Mapped[list["StoryPermission"]] = relationship(
        "StoryPermission", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"


class StoryPermission(Base):
    __tablename__ = "story_permissions"

    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)

    can_read: Mapped[bool] = mapped_column(Boolean, default=True)
    can_download: Mapped[bool] = mapped_column(Boolean, default=False)
    can_delete: Mapped[bool] = mapped_column(Boolean, default=False)

    story: Mapped["Story"] = relationship("Story", back_populates="permissions")
    group: Mapped["Group"] = relationship("Group", back_populates="story_permissions")
