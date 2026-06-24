# novelcast/db/repositories/settings_repository.py

import json

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.settings import ServerSetting, UserSetting


class SettingsRepository(BaseRepository):

    def __init__(self, session_factory, on_change=None):
        super().__init__(session_factory)
        self.on_change = on_change  # callable(key: str) | None

    # ── server settings ───────────────────────────────────────────────────
    # (unchanged - no modifications needed)

    def get_server_setting(self, key: str):
        with self.session_no_commit() as db:
            row = db.get(ServerSetting, key)
            return _deserialize(row.value) if row else None

    def get_all_server_settings(self) -> dict:
        with self.session_no_commit() as db:
            rows = db.scalars(select(ServerSetting)).all()
            return {row.key: _deserialize(row.value) for row in rows}

    def get_server_settings_by_prefix(self, prefix: str) -> dict:
        """Return {full_key: value} for every key starting with *prefix*."""
        with self.session_no_commit() as db:
            rows = db.scalars(select(ServerSetting)).all()
            return {
                row.key: _deserialize(row.value)
                for row in rows
                if row.key.startswith(prefix)
            }

    def set_server_setting(self, key: str, value) -> None:
        with self.session() as db:
            stmt = (
                insert(ServerSetting)
                .values(key=key, value=json.dumps(value))
                .on_conflict_do_update(
                    index_elements=["key"],
                    set_={"value": json.dumps(value)},
                )
            )
            db.execute(stmt)

        if self.on_change:
            self.on_change(key)

    def delete_server_setting(self, key: str) -> None:
        with self.session() as db:
            row = db.get(ServerSetting, key)
            if row:
                db.delete(row)

        if self.on_change:
            self.on_change(key)

    # ── user settings ─────────────────────────────────────────────────────

    def get_user_settings(self, user_id: int) -> dict | None:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(UserSetting).where(UserSetting.user_id == user_id)
            ).all()

            if not rows:
                return None

            # reconstruct the flat dict the SettingsService expects
            result = {"user_id": user_id}
            for row in rows:
                result[row.name] = _deserialize(row.value)
            return result

    def set_user_setting(
        self,
        user_id: int,
        name: str,
        value,
        category: str = "preference",
        type_: str = "json",
    ) -> None:
        with self.session() as db:
            stmt = (
                insert(UserSetting)
                .values(
                    user_id=user_id,
                    name=name,
                    value=json.dumps(value),
                    category=category,
                    type=type_,
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "name"],
                    set_={"value": json.dumps(value)},
                )
            )
            db.execute(stmt)

    def delete_user_setting(self, user_id: int, name: str) -> None:
        with self.session() as db:
            row = db.scalar(
                select(UserSetting).where(
                    UserSetting.user_id == user_id,
                    UserSetting.name == name,
                )
            )
            if row:
                db.delete(row)

    def save_user_settings(
        self,
        user_id: int,
        theme: str,
        font_size: int,
        line_height: float,
        auto_update: int,
        # NEW: Chapter reading settings
        chapter_theme: str = None,
        chapter_font_family: str = None,
        chapter_font_size: int = None,
        chapter_line_spacing: int = None,
        chapter_font_weight: int = None,
        chapter_paragraph_spacing: int = None,
    ) -> None:
        """Save user settings including chapter reading preferences as key-value pairs."""
        
        # Build the settings dict: name → (value, category, type)
        settings = {
            # Display settings
            "theme":       (theme,        "display", "str"),
            "font_size":   (font_size,    "display", "int"),
            "line_height": (line_height,  "display", "float"),
            "auto_update": (auto_update,  "display", "int"),
        }

        # NEW: Add chapter reading settings (only if provided)
        if chapter_theme is not None:
            settings["chapter_theme"] = (chapter_theme, "reading", "str")
        if chapter_font_family is not None:
            settings["chapter_font_family"] = (chapter_font_family, "reading", "str")
        if chapter_font_size is not None:
            settings["chapter_font_size"] = (chapter_font_size, "reading", "int")
        if chapter_line_spacing is not None:
            settings["chapter_line_spacing"] = (chapter_line_spacing, "reading", "int")
        if chapter_font_weight is not None:
            settings["chapter_font_weight"] = (chapter_font_weight, "reading", "int")
        if chapter_paragraph_spacing is not None:
            settings["chapter_paragraph_spacing"] = (chapter_paragraph_spacing, "reading", "int")

        # Upsert each setting as a row in UserSetting table
        with self.session() as db:
            for name, (value, category, type_) in settings.items():
                stmt = (
                    insert(UserSetting)
                    .values(
                        user_id=user_id,
                        name=name,
                        value=json.dumps(value),
                        category=category,
                        type=type_,
                    )
                    .on_conflict_do_update(
                        index_elements=["user_id", "name"],
                        set_={"value": json.dumps(value)},
                    )
                )
                db.execute(stmt)


# ── helpers ───────────────────────────────────────────────────────────────

def _deserialize(value: str):
    """Deserialize JSON string to Python value."""
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
