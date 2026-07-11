# novelcast/db/models/author.py

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.author_link import AuthorLink
    from novelcast.db.models.story import Story


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    picture_path: Mapped[str | None] = mapped_column(String)  # local path or URL

    stories: Mapped[list["Story"]] = relationship("Story", secondary="story_author", back_populates="authors")
    links: Mapped[list["AuthorLink"]] = relationship(
        "AuthorLink",
        back_populates="author",
        cascade="all, delete-orphan",
        order_by="AuthorLink.label",
    )

    def __repr__(self) -> str:
        return f"<Author id={self.id} name={self.name!r}>"
