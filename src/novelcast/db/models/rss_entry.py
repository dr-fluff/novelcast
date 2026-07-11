# novelcast/db/models/rss_entry.py

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from novelcast.db.base import Base


class RssEntry(Base):
    __tablename__ = "rss_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source: Mapped[str] = mapped_column(
        String,
        index=True,
        nullable=False,
    )

    guid: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String,
    )

    link: Mapped[str | None] = mapped_column(
        String,
    )

    published: Mapped[datetime | None] = mapped_column(
        DateTime,
    )

    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
