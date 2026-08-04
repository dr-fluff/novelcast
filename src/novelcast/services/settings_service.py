# novelcast/services/settings_service.py

import logging
from typing import Any, NamedTuple

from novelcast.utils.secrets import decrypt_secret, encrypt_secret, is_encrypted_secret

logger = logging.getLogger(__name__)

_SITE_PREFIX = "fanficfare.site."

_READING_KEY_MAP = {
    "chapter_theme": "theme",
    "chapter_font_family": "fontFamily",
    "chapter_font_size": "fontSize",
    "chapter_line_spacing": "lineSpacing",
    "chapter_font_weight": "fontWeight",
    "chapter_paragraph_spacing": "paragraphSpacing",
    "chapter_content_padding": "contentPadding",
}


class SettingValue(NamedTuple):
    key: str
    value: Any
    type: str
    description: str | None
    label: str | None


class SettingsService:
    def __init__(
        self,
        repo,
        settings_schema=None,
        user_settings_schema=None,
        required_user_settings=None,
        secret_key: str = "",
    ):

        if required_user_settings is None:
            raise ValueError("required_user_settings must be provided")

        self.user_settings_schema = user_settings_schema or {}
        self.required_user_settings = required_user_settings or set()
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
        if value is None:
            return default
        return self._coerce_setting_value(key, value)

    def set_server_setting(self, key: str, value):
        if not key or "." not in key:
            logger.warning("Invalid server setting key: %s", key)
            return None

        meta = self._get_schema_meta(key)
        value = self._coerce_setting_value(key, value, meta=meta)

        if self._is_secret_key(key):
            if value == "":
                return None

            current_encrypted = self.repo.get_server_setting(key)
            current_plain = self._decrypt_secret_value(current_encrypted) if current_encrypted else ""

            if str(value) == str(current_plain):
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

                value = self._coerce_setting_value(full_key, value, meta=meta)

                if self._is_secret_key(full_key):
                    value = self._decrypt_secret_value(value)

                resolved[section][key] = value

        return resolved

    def get_field_meta(self, section: str, key: str) -> dict:
        return self.schema.get(section, {}).get(key, {})

    def get(self, dotted_key: str, default=None) -> SettingValue:
        section, _, field = dotted_key.partition(".")
        meta = self.schema.get(section, {}).get(field)

        if meta is None:
            logger.warning("Unknown setting key requested: %s", dotted_key)
            return SettingValue(
                key=dotted_key,
                value=default,
                type="unknown",
                description=None,
                label=None,
            )

        value = self.repo.get_server_setting(dotted_key)
        if value is None and meta.get("legacy_key"):
            value = self.repo.get_server_setting(meta["legacy_key"])
        if value is None:
            value = meta.get("default", default)

        value = self._coerce_setting_value(dotted_key, value, meta=meta)

        if meta.get("type") == "secret":
            value = self._decrypt_secret_value(value)

        return SettingValue(
            key=dotted_key,
            value=value,
            type=meta.get("type", "unknown"),
            description=meta.get("description"),
            label=meta.get("label"),
        )

    def get_section(self, section: str) -> dict:
        return self.get_resolved_server_settings().get(section, {})

    def migrate_server_secrets(self):
        db_values = self.get_server_settings()

        for section, fields in self.schema.items():
            if not isinstance(fields, dict):
                logger.warning(f"BAD SCHEMA SECTION: {section!r} -> {type(fields)} = {fields!r}")
                continue

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
                        or (self.repo.get_server_setting(meta["legacy_key"]) if meta.get("legacy_key") else None)
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

    def _get_schema_meta(self, key: str) -> dict | None:
        if "." not in key:
            return None

        section, field = key.split(".", 1)
        return self.schema.get(section, {}).get(field)

    def _coerce_setting_value(self, key: str, value, meta=None):
        if meta is None:
            meta = self._get_schema_meta(key)

        if meta is None:
            return value

        if meta.get("type") != "bool":
            return value

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return bool(value)

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off", ""}:
                return False

        return bool(value)

    def _is_secret_key(self, key: str) -> bool:
        if "." not in key:
            return False

        meta = self._get_schema_meta(key)
        return meta is not None and meta.get("type") == "secret"

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
            self.schema.get("fanficfare", {}).get("site_overrides", {}).get("default", {})
        )
        sites: dict[str, dict] = {domain: dict(fields) for domain, fields in schema_defaults.items()}

        raw = self.repo.get_server_settings_by_prefix(_SITE_PREFIX)
        for full_key, value in raw.items():
            remainder = full_key[len(_SITE_PREFIX) :]
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
        fields = self.schema.get("fanficfare", {}).get("site_overrides", {}).get("fields", {})
        return fields.get(field, {}).get("type") == "secret"

    # ─────────────────────────────
    # USER SETTINGS (schema-driven, device-aware)
    # ─────────────────────────────

    def _sanitize_setting(self, key: str, value):
        """Validate/coerce a single user setting value against its schema spec."""
        spec = self.user_settings_schema[key]
        t = spec["type"]

        if t == "choice":
            return value if value in spec["choices"] else spec["default"]

        if t == "bool":
            return 1 if str(value) in ("1", "true", "True") else 0

        if t == "int_range":
            try:
                v = int(value)
            except (TypeError, ValueError):
                return spec["default"]
            return max(spec["min"], min(v, spec["max"]))

        if t == "float_range":
            try:
                v = float(value)
            except (TypeError, ValueError):
                return spec["default"]
            return max(spec["min"], min(v, spec["max"]))

        return value

    def get_user_settings(self, user_id: int, device_id: str | None = None) -> dict:
        row = self.repo.get_user_settings(user_id, device_id=device_id) or {}

        result = {"user_id": row.get("user_id", user_id)}
        for key, spec in self.user_settings_schema.items():
            result[key] = row.get(key, spec["default"])

        return result

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

    def save_user_settings(self, user_id: int, device_id: str | None = None, **kwargs):

        current = self.get_user_settings(user_id, device_id=device_id)
        sanitized = {}

        for key in self.required_user_settings:
            value = kwargs.get(key)
            if value is not None:
                sanitized[key] = self._sanitize_setting(key, value)
            else:
                spec = self.user_settings_schema[key]
                sanitized[key] = current.get(key, spec["default"])

        for key, value in kwargs.items():
            if key in self.required_user_settings or key not in self.user_settings_schema:
                continue
            if value is None:
                continue
            sanitized[key] = self._sanitize_setting(key, value)

        return self.repo.save_user_settings(user_id, device_id=device_id, **sanitized)

    def get_chapter_reading_settings(self, user_id: int, device_id: str | None = None) -> dict:
        """Get only chapter reading settings (for reader JS API), keyed by
        the JS-facing field names (theme, fontFamily, fontSize, ...)."""
        settings = self.get_user_settings(user_id, device_id=device_id)
        return {
            js_key: settings.get(schema_key, self.user_settings_schema[schema_key]["default"])
            for schema_key, js_key in _READING_KEY_MAP.items()
        }

    def get_reading_settings_schema(self) -> dict:
        return {js_key: self.user_settings_schema[schema_key] for schema_key, js_key in _READING_KEY_MAP.items()}
