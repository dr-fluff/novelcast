"""
novelcast/db/models/jobs.py
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.story import Story


class UpdateJob(Base):
    __tablename__ = "update_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String, default="pending")
    last_run: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_run: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error: Mapped[Optional[str]] = mapped_column(Text)

    story: Mapped[Optional["Story"]] = relationship("Story", back_populates="update_jobs")

    def __repr__(self) -> str:
        return f"<UpdateJob id={self.id} story_id={self.story_id} status={self.status!r}>"
