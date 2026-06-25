# novelcast/services/settings_service.py

import logging

from novelcast.utils.secrets import decrypt_secret, encrypt_secret, is_encrypted_secret

logger = logging.getLogger(__name__)

_SITE_PREFIX = "fanficfare.site."


class SettingsService:
    def __init__(self, repo, settings_schema=None, secret_key: str = ""):
        self.repo = repo
        self.schema = settings_schema or {}
        self.secret_key = secret_key

    # ─────────────────────────────
    # SERVER SETTINGS (unchanged)
    # ─────────────────────────────

    def get_scoped_server_settings(self) -> dict:
        resolved = self.get_resolved_server_settings()

        grouped = {}

        for section, fields in self.schema.items():
            grouped[section] = {}

            for key, meta in fields.items():
                if meta.get("type") == "site_map":
                    continue

                scope = meta.get("scope", "defaults")
                value = resolved.get(section, {}).get(key)

                grouped[section].setdefault(scope, {})
                grouped[section][scope][key] = value

        return grouped
    
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
        db_values = self.get_server_settings()
        resolved = {}

        for section, fields in self.schema.items():
            resolved[section] = {}

            for key, meta in fields.items():
                if meta.get("type") == "site_map":
                    continue

                full_key = f"{section}.{key}"
                value = db_values.get(full_key)
                if value is None and meta.get("legacy_key"):
                    value = db_values.get(meta["legacy_key"])
                if value is None:
                    value = meta.get("default")

                if self._is_secret_key(full_key):
                    value = self._decrypt_secret_value(value)

                resolved[section][key] = value

        return resolved
    
    def get_field_meta(self, section: str, key: str) -> dict:
        return self.schema.get(section, {}).get(key, {})

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
            for key, meta in fields.items():
                if meta.get("type") == "site_map":
                    continue

                full_key = f"{section}.{key}"
                if self._is_secret_key(full_key):
                    resolved.setdefault(section, {})[key] = bool(
                        self.repo.get_server_setting(full_key)
                        or (
                            self.repo.get_server_setting(meta["legacy_key"])
                            if meta.get("legacy_key")
                            else None
                        )
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
    # SITE OVERRIDES (unchanged)
    # ─────────────────────────────

    def get_site_overrides(self) -> dict[str, dict]:
        schema_defaults: dict[str, dict] = (
            self.schema
            .get("fanficfare", {})
            .get("site_overrides", {})
            .get("default", {})
        )
        sites: dict[str, dict] = {
            domain: dict(fields)
            for domain, fields in schema_defaults.items()
        }

        raw = self.repo.get_server_settings_by_prefix(_SITE_PREFIX)
        for full_key, value in raw.items():
            remainder = full_key[len(_SITE_PREFIX):]
            domain, sep, field = remainder.rpartition(".")
            if not sep or not domain or not field:
                logger.warning("Malformed site override key: %s", full_key)
                continue

            if self._is_secret_site_field(field):
                value = self._decrypt_secret_value(value)

            sites.setdefault(domain, {})[field] = value

        return sites

    def set_site_override(self, domain: str, field: str, value) -> None:
        if not domain or not field:
            raise ValueError("domain and field must be non-empty strings")

        key = f"{_SITE_PREFIX}{domain}.{field}"

        if self._is_secret_site_field(field):
            if value == "":
                return
            value = encrypt_secret(str(value), self.secret_key)

        self.repo.set_server_setting(key, value)

    def delete_site_override(self, domain: str, field: str | None = None) -> None:
        if field:
            self.repo.delete_server_setting(f"{_SITE_PREFIX}{domain}.{field}")
        else:
            prefix = f"{_SITE_PREFIX}{domain}."
            keys = self.repo.get_server_settings_by_prefix(prefix)
            for key in keys:
                self.repo.delete_server_setting(key)

    def _is_secret_site_field(self, field: str) -> bool:
        fields = (
            self.schema
            .get("fanficfare", {})
            .get("site_overrides", {})
            .get("fields", {})
        )
        return fields.get(field, {}).get("type") == "secret"

    # ─────────────────────────────
    # USER SETTINGS (UPDATED)
    # ─────────────────────────────

    def get_user_settings(self, user_id: int):
        """Get all user settings including chapter reading preferences."""
        row = self.repo.get_user_settings(user_id)

        defaults = {
            "user_id": user_id,
            # Display settings (existing)
            "theme": "light",
            "font_size": 14,
            "line_height": 1.5,
            "auto_update": 1,
            # Chapter reading settings (new)
            "chapter_theme": "light",
            "chapter_font_family": "serif",
            "chapter_font_size": 100,
            "chapter_line_spacing": 100,
            "chapter_font_weight": 0,
            "chapter_paragraph_spacing": 100,
            "chapter_content_padding": 3,
        }

        if not row:
            return defaults

        return {
            "user_id": row.get("user_id", user_id),
            # Display settings
            "theme": row.get("theme", "light"),
            "font_size": row.get("font_size", 14),
            "line_height": row.get("line_height", 1.5),
            "auto_update": row.get("auto_update", 1),
            # Chapter reading settings
            "chapter_theme": row.get("chapter_theme", "light"),
            "chapter_font_family": row.get("chapter_font_family", "serif"),
            "chapter_font_size": row.get("chapter_font_size", 100),
            "chapter_line_spacing": row.get("chapter_line_spacing", 100),
            "chapter_font_weight": row.get("chapter_font_weight", 0),
            "chapter_paragraph_spacing": row.get("chapter_paragraph_spacing", 100),
            "chapter_content_padding": row.get("chapter_content_padding", 3),
        }

    def get_user_preference(self, user_id: int, key: str, default=None):
        row = self.repo.get_user_settings(user_id) or {}
        return row.get(key, default)

    def set_user_preference(self, user_id: int, key: str, value) -> None:
        self.repo.set_user_setting(
            user_id=user_id,
            name=key,
            value=value,
            category="preference",
            type_="json",
        )

    def delete_user_preference(self, user_id: int, key: str) -> None:
        self.repo.delete_user_setting(user_id, key)

    def save_user_settings(
        self,
        user_id: int,
        theme: str,
        font_size,
        line_height,
        auto_update,
        # NEW: Chapter reading settings
        chapter_theme: str = None,
        chapter_font_family: str = None,
        chapter_font_size: int = None,
        chapter_line_spacing: int = None,
        chapter_font_weight: int = None,
        chapter_paragraph_spacing: int = None,
        chapter_content_padding: int = None, 
    ):
        """Sanitized write to avoid corrupted DB values from forms."""

        # Validate & sanitize display settings
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

        # NEW: Validate & sanitize chapter reading settings
        if chapter_theme is not None:
            chapter_theme = chapter_theme if chapter_theme in ("light", "sepia", "dark") else "light"

        if chapter_font_family is not None:
            chapter_font_family = chapter_font_family if chapter_font_family in ("serif", "sans") else "serif"

        if chapter_font_size is not None:
            try:
                chapter_font_size = max(80, min(int(chapter_font_size), 170))
            except Exception:
                chapter_font_size = 100

        if chapter_line_spacing is not None:
            try:
                chapter_line_spacing = max(80, min(int(chapter_line_spacing), 150))
            except Exception:
                chapter_line_spacing = 100

        if chapter_font_weight is not None:
            try:
                chapter_font_weight = max(-30, min(int(chapter_font_weight), 100))
            except Exception:
                chapter_font_weight = 0

        if chapter_paragraph_spacing is not None:
            try:
                chapter_paragraph_spacing = max(50, min(int(chapter_paragraph_spacing), 200))
            except Exception:
                chapter_paragraph_spacing = 100
        
        if chapter_content_padding is not None:
            try:
                chapter_content_padding = max(3, min(int(chapter_content_padding), 20))
            except Exception:
                chapter_content_padding = 3

        return self.repo.save_user_settings(
            user_id,
            theme,
            font_size,
            line_height,
            auto_update,
            chapter_theme=chapter_theme,
            chapter_font_family=chapter_font_family,
            chapter_font_size=chapter_font_size,
            chapter_line_spacing=chapter_line_spacing,
            chapter_font_weight=chapter_font_weight,
            chapter_paragraph_spacing=chapter_paragraph_spacing,
            chapter_content_padding=chapter_content_padding, 
        )

    # NEW: Convenience method for chapter reader JS
    def get_chapter_reading_settings(self, user_id: int) -> dict:
        """Get only chapter reading settings (for reader JS API)."""
        settings = self.get_user_settings(user_id)
        return {
            "theme": settings.get("chapter_theme", "light"),
            "fontFamily": settings.get("chapter_font_family", "serif"),
            "fontSize": settings.get("chapter_font_size", 100),
            "lineSpacing": settings.get("chapter_line_spacing", 100),
            "fontWeight": settings.get("chapter_font_weight", 0),
            "paragraphSpacing": settings.get("chapter_paragraph_spacing", 100),
            "contentPadding": settings.get("chapter_content_padding", 3), 
        }
