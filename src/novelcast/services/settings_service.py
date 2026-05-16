# novelcast/services/settings_service.py

import logging

from novelcast.utils.secrets import decrypt_secret, encrypt_secret, is_encrypted_secret

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, repo, settings_schema=None, secret_key: str = ""):
        self.repo = repo
        self.schema = settings_schema or {}
        self.secret_key = secret_key

    # ─────────────────────────────
    # SERVER SETTINGS
    # ─────────────────────────────
    def get_server_setting(self, key: str, default=None):
        value = self.repo.get_server_setting(key)
        return default if value is None else value

    def set_server_setting(self, key: str, value):
        if not key or "." not in key:
            logger.warning("Invalid server setting key: %s", key)
            return None

        if self._is_secret_key(key):
            if value == "":
                return None
            value = encrypt_secret(str(value), self.secret_key)

        return self.repo.set_server_setting(key, value)

    def get_server_settings(self):
        return self.repo.get_all_server_settings() or {}

    def get_resolved_server_settings(self):
        """
        Merge DB values + schema defaults
        """
        db_values = self.get_server_settings()
        resolved = {}

        for section, fields in self.schema.items():
            resolved[section] = {}

            for key, meta in fields.items():
                full_key = f"{section}.{key}"
                value = db_values.get(
                    full_key,
                    meta.get("default"),
                )
                if self._is_secret_key(full_key):
                    value = self._decrypt_secret_value(value)
                resolved[section][key] = value

        return resolved

    def migrate_server_secrets(self):
        db_values = self.get_server_settings()

        for section, fields in self.schema.items():
            for key, meta in fields.items():
                if meta.get("type") != "secret":
                    continue

                full_key = f"{section}.{key}"
                value = db_values.get(full_key)
                if value and not is_encrypted_secret(value):
                    self.repo.set_server_setting(
                        full_key,
                        encrypt_secret(str(value), self.secret_key),
                    )

    def get_display_server_settings(self):
        resolved = self.get_resolved_server_settings()

        for section, fields in self.schema.items():
            for key in fields:
                full_key = f"{section}.{key}"
                if self._is_secret_key(full_key):
                    resolved.setdefault(section, {})[key] = bool(
                        self.repo.get_server_setting(full_key)
                    )

        return resolved

    def get_raw_server_setting(self, key: str, default=None):
        value = self.repo.get_server_setting(key)
        return default if value is None else value

    def get_secret(self, key: str, default=""):
        value = self.repo.get_server_setting(key)
        if value is None:
            return default
        return self._decrypt_secret_value(value)

    def _is_secret_key(self, key: str) -> bool:
        if "." not in key:
            return False

        section, field = key.split(".", 1)
        meta = self.schema.get(section, {}).get(field, {})
        return meta.get("type") == "secret"

    def _decrypt_secret_value(self, value):
        if not value:
            return ""

        if not is_encrypted_secret(value):
            return value

        return decrypt_secret(value, self.secret_key)

    # ─────────────────────────────
    # USER SETTINGS
    # ─────────────────────────────
    def get_user_settings(self, user_id: int):
        row = self.repo.get_user_settings(user_id)

        defaults = {
            "user_id": user_id,
            "theme": "light",
            "font_size": 14,
            "line_height": 1.5,
            "auto_update": 1,
        }

        if not row:
            return defaults

        return {
            "user_id": row.get("user_id", user_id),
            "theme": row.get("theme", "light"),
            "font_size": row.get("font_size", 14),
            "line_height": row.get("line_height", 1.5),
            "auto_update": row.get("auto_update", 1),
        }

    def save_user_settings(
        self,
        user_id: int,
        theme: str,
        font_size: int,
        line_height: float,
        auto_update: int,
    ):
        """
        Sanitized write to avoid corrupted DB values from forms
        """

        theme = theme if theme in ("light", "dark") else "light"

        try:
            font_size = max(10, min(int(font_size), 30))
        except Exception:
            font_size = 14

        try:
            line_height = float(line_height)
            line_height = max(1.0, min(line_height, 2.5))
        except Exception:
            line_height = 1.5

        auto_update = 1 if str(auto_update) in ("1", "true", "True") else 0

        return self.repo.save_user_settings(
            user_id,
            theme,
            font_size,
            line_height,
            auto_update,
        )
