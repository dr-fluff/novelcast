"""
novelcast/db/models/progress.py
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.chapter import Chapter
    from novelcast.db.models.story import Story
    from novelcast.db.models.user import User


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True)

    # "Continue reading" pointer — wherever the user MOST RECENTLY read,
    # regardless of direction. Updated unconditionally on every save.
    last_chapter_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="SET NULL"))
    last_position: Mapped[int] = mapped_column(Integer, default=0)

    # Furthest chapter ever reached — forward-only, used for read/unread
    # marking on the story page. Deliberately separate from
    # last_chapter_id so going back to re-read an earlier chapter
    # doesn't affect what's considered "read" or move the unread
    # boundary backwards.
    furthest_chapter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="SET NULL")
    )

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="reading_progress")
    story: Mapped["Story"] = relationship("Story", back_populates="reading_progress")
    last_chapter: Mapped[Optional["Chapter"]] = relationship("Chapter", foreign_keys=[last_chapter_id])
    furthest_chapter: Mapped[Optional["Chapter"]] = relationship("Chapter", foreign_keys=[furthest_chapter_id])