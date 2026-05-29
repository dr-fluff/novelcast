# novelcast/db/models/story_link.py

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base


class StoryLink(Base):
    __tablename__ = "story_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE")
    )

    label: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)

    story = relationship("Story", back_populates="links")