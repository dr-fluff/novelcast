# novelcast/db/models/story.py


from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.author import Author
    from novelcast.db.models.chapter import Chapter
    from novelcast.db.models.group import StoryPermission
    from novelcast.db.models.progress import ReadingProgress
    from novelcast.db.models.settings import StorySetting
    from novelcast.db.models.jobs import UpdateJob


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, unique=True)

    # kept for quick display without joining authors; populate from Author on upsert
    author: Mapped[Optional[str]] = mapped_column(String)

    local_path: Mapped[Optional[str]] = mapped_column(String, unique=True)
    cover_path: Mapped[Optional[str]] = mapped_column(String)

    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_chapters: Mapped[int] = mapped_column(Integer, default=0)
    latest_online_chapter: Mapped[Optional[int]] = mapped_column(Integer)
    latest_downloaded_chapter: Mapped[Optional[int]] = mapped_column(Integer)
    online_chapters: Mapped[int] = mapped_column(Integer, default=0)

    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    authors: Mapped[list["Author"]] = relationship(
        "Author",
        secondary="story_author",
        back_populates="stories",
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter",
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_number",
    )
    permissions: Mapped[list["StoryPermission"]] = relationship(
        "StoryPermission",
        back_populates="story",
        cascade="all, delete-orphan",
    )
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(
        "ReadingProgress",
        back_populates="story",
        cascade="all, delete-orphan",
    )
    settings: Mapped[list["StorySetting"]] = relationship(
        "StorySetting",
        back_populates="story",
        cascade="all, delete-orphan",
    )
    update_jobs: Mapped[list["UpdateJob"]] = relationship(
        "UpdateJob",
        back_populates="story",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Story id={self.id} title={self.title!r}>"
