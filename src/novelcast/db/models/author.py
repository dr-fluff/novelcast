# novelcast/db/models/author.py


from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.story import Story


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    profile_url: Mapped[Optional[str]] = mapped_column(String)

    stories: Mapped[list["Story"]] = relationship("Story",secondary="story_author",back_populates="authors",)

    def __repr__(self) -> str:
        return f"<Author id={self.id} name={self.name!r}>"
