# novelcast/db/models/tag.py

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    stories = relationship(
        "Story",
        secondary="story_tags",
        back_populates="tags",
    )

    def __repr__(self):
        return f"<Tag {self.name}>"