# novelcast/db/models/settings.py 
#
# Add UniqueConstraint to UserSetting so the upsert in SettingsRepository works.

from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from novelcast.db.base import Base

if TYPE_CHECKING:
    from novelcast.db.models.user import User
    from novelcast.db.models.story import Story


class ServerSetting(Base):
    __tablename__ = "server_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="str")

    def __repr__(self) -> str:
        return f"<ServerSetting key={self.key!r}>"


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_settings_user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="str")

    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSetting user_id={self.user_id} name={self.name!r}>"


class StorySetting(Base):
    __tablename__ = "story_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    story_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="str")

    story: Mapped["Story"] = relationship("Story", back_populates="settings")

    def __repr__(self) -> str:
        return f"<StorySetting story_id={self.story_id} name={self.name!r}>"
