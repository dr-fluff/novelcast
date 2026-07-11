# novelcast/db/models/author_link.py

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if False:
    from novelcast.db.models.author import Author


class AuthorLink(Base):
    __tablename__ = "author_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)

    author: Mapped["Author"] = relationship("Author", back_populates="links")

    def __repr__(self) -> str:
        return f"<AuthorLink id={self.id} label={self.label!r}>"
