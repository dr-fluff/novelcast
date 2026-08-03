# novelcast/db/models/chapter.py


from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.story import Story


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)

    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)  # online index (1..N)
    title: Mapped[Optional[str]] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String, unique=True)  # stable scrape key

    # True once at least one ChapterFile exists and the canonical HTML is ready
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)

    # Word count of the canonical chapter text. Populated once the chapter
    # is downloaded/parsed; used for reading-speed stats (words / read time).
    # NULL until computed, so existing chapters degrade gracefully rather
    # than reporting 0.
    word_count: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    story: Mapped["Story"] = relationship("Story", back_populates="chapters")
    files: Mapped[list["ChapterFile"]] = relationship(
        "ChapterFile",
        back_populates="chapter",
        cascade="all, delete-orphan",
    )

    @property
    def html_file(self) -> Optional["ChapterFile"]:
        """Shortcut to the canonical HTML file for reading."""
        for f in self.files:
            if f.is_canonical:
                return f
        return None

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} story_id={self.story_id} number={self.chapter_number}>"


class ChapterFile(Base):
    """
    One row per file on disk for a chapter.
    A chapter can have multiple files (original download + converted HTML, etc.).
    Exactly one should have is_canonical=True — the HTML used for reading.
    """

    __tablename__ = "chapter_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)

    file_path: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)  # "html", "epub", "txt", etc.
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False)  # the HTML for reading

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="files")

    def __repr__(self) -> str:
        return f"<ChapterFile id={self.id} chapter_id={self.chapter_id} format={self.format!r}>"


class ChapterProgress(Base):
    __tablename__ = "chapter_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    anchor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("user_id", "chapter_id", name="uq_chapter_progress_user_chapter"),)