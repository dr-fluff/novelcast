"""
novelcast/db/models/stats.py
"""

from datetime import date as date_
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.user import User


class UserDailyActivity(Base):
    """
    One row per user per calendar day (UTC) they were active. Sum of
    read_seconds across all rows gives total read time; row count over
    the last year drives the GitHub-style activity heatmap.
    """

    __tablename__ = "user_daily_activity"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    activity_date: Mapped[date_] = mapped_column(Date, primary_key=True)

    read_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="daily_activity")

    def __repr__(self) -> str:
        return f"<UserDailyActivity user_id={self.user_id} date={self.activity_date} read_seconds={self.read_seconds}>"


class UserDevice(Base):
    """
    One row per (user, device) pair seen. device_id matches the existing
    nc_device_id convention already used for device-scoped UserSetting rows,
    so this reuses an identifier the client already generates and sends —
    no new client-side concept.
    """

    __tablename__ = "user_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(String, nullable=False)

    # Optional human-readable label, e.g. derived from User-Agent at first
    # sight ("iPad Air"), or later user-editable.
    label: Mapped[str | None] = mapped_column(String)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="devices")

    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_user_devices_user_device"),)

    def __repr__(self) -> str:
        return f"<UserDevice user_id={self.user_id} device_id={self.device_id!r} label={self.label!r}>"
