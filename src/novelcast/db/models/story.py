from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.author import Author
    from novelcast.db.models.chapter import Chapter
    from novelcast.db.models.genre import Genre
    from novelcast.db.models.group import StoryPermission
    from novelcast.db.models.jobs import UpdateJob
    from novelcast.db.models.progress import ReadingProgress
    from novelcast.db.models.series import Series
    from novelcast.db.models.settings import StorySetting
    from novelcast.db.models.tag import Tag


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── core metadata ──────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String)

    story_site_id: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String, unique=True)

    # cached display (optional denormalization)
    author: Mapped[str | None] = mapped_column(String)

    publish_year: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String)

    description: Mapped[str | None] = mapped_column(Text)

    # ── metadata override tracking ───────────────────────────────────────
    # JSON list of field names ("title", "author", "subtitle", "description",
    # "publish_year", "language", "series", "genres", "tags") the user has
    # manually edited via the GUI. Scrape/sync updates skip any field name
    # present here so re-syncing never clobbers a manual edit. Set/cleared
    # only by StoriesRepository.update_full_metadata().
    locked_fields: Mapped[str | None] = mapped_column(Text)

    # ── files ──────────────────────────────────────────────────────────────
    cover_path: Mapped[str | None] = mapped_column(String)
    local_img_path: Mapped[str | None] = mapped_column(String)
    local_path: Mapped[str | None] = mapped_column(String, unique=True)

    # ── chapter stats ─────────────────────────────────────────────────────
    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_chapters: Mapped[int] = mapped_column(Integer, default=0)
    latest_online_chapter: Mapped[int | None] = mapped_column(Integer)
    latest_downloaded_chapter: Mapped[int | None] = mapped_column(Integer)
    online_chapters: Mapped[int] = mapped_column(Integer, default=0)

    # ── timestamps ────────────────────────────────────────────────────────
    last_updated: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # ── relationships ──────────────────────────────────────────────────────

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

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="story_tags",
        back_populates="stories",
    )

    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary="story_genres",
        back_populates="stories",
    )

    series: Mapped[list["Series"]] = relationship(
        "Series",
        secondary="story_series",
        back_populates="stories",
    )

    def __repr__(self) -> str:
        return f"<Story id={self.id} title={self.title!r}>"
