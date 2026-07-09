# novelcast/db/repositories/settings_repository.py

import json
import logging

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.settings import ServerSetting, UserSetting

logger = logging.getLogger(__name__)

def _storage_type_for(spec: dict) -> str:
    """Derive the UserSetting.type column value from a schema spec."""
    t = spec.get("type")
    if t == "bool":
        return "int"
    if t == "int_range":
        return "int"
    if t == "float_range":
        return "float"
    if t == "choice":
        default = spec.get("default")
        # choices can be strings (theme) or ints (font_size, font_weight)
        if isinstance(default, int) and not isinstance(default, bool):
            return "int"
        return "str"
    return "json"


class SettingsRepository(BaseRepository):
    DEVICE_PREFIX = "device:"

    def __init__(self, session_factory, user_settings_schema=None, on_change=None):
        super().__init__(session_factory)
        self.user_settings_schema = user_settings_schema or {}
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

    def get_user_settings(self, user_id: int, device_id: str | None = None) -> dict | None:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(UserSetting).where(UserSetting.user_id == user_id)
            ).all()

            if not rows:
                return None

            result = {"user_id": user_id}
            device_prefix = f"{self.DEVICE_PREFIX}{device_id}." if device_id else None
            device_overrides = {}

            for row in rows:
                if row.name.startswith(self.DEVICE_PREFIX):
                    if device_prefix and row.name.startswith(device_prefix):
                        device_overrides[row.name[len(device_prefix):]] = _deserialize(row.value)
                    # rows belonging to a *different* device are ignored
                    continue
                result[row.name] = _deserialize(row.value)

            result.update(device_overrides)
            return result

    def save_user_settings(self, user_id: int, device_id: str | None = None, **kwargs) -> None:
        """Bulk, schema-driven upsert. Used for reading/preference settings
        that are defined in user_settings_schema (category derived from spec)."""
        with self.session() as db:
            for name, value in kwargs.items():
                spec = self.user_settings_schema.get(name, {})
                category = spec.get("category", "preference")
                type_ = _storage_type_for(spec)

                if category == "reading" and not device_id:
                    logger.warning(
                        "Skipping save of reading setting %r for user %s: no device_id provided",
                        name, user_id,
                    )
                    continue

                stored_name = name
                if category == "reading":
                    stored_name = f"{self.DEVICE_PREFIX}{device_id}.{name}"

                stmt = (
                    insert(UserSetting)
                    .values(
                        user_id=user_id,
                        name=stored_name,
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

    def set_user_setting(
        self,
        user_id: int,
        name: str,
        value,
        category: str = "preference",
        type_: str = "json",
    ) -> None:
        """Single-key upsert for arbitrary, non-schema user preferences
        (e.g. device.{id}.library.index). Unlike save_user_settings, this
        does not consult user_settings_schema — the caller supplies the
        fully-qualified name and its own category/type."""
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


# ── helpers ───────────────────────────────────────────────────────────────

def _deserialize(value: str):
    """Deserialize JSON string to Python value."""
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Failed to deserialize value: %r", value)
        return value