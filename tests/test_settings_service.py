from novelcast.core.defaults import REQUIRED_USER_SETTINGS, SETTINGS, USER_SETTINGS_SCHEMA
from novelcast.services.settings_service import SettingsService


class DummySettingsRepository:
    def __init__(self, values=None):
        self.values = values or {}

    def get_server_setting(self, key):
        return self.values.get(key)

    def get_all_server_settings(self):
        return dict(self.values)

    def set_server_setting(self, key, value):
        self.values[key] = value

    def get_server_settings_by_prefix(self, prefix):
        return {k: v for k, v in self.values.items() if k.startswith(prefix)}

    def get_user_settings(self, user_id, device_id=None):
        return None


def test_server_bool_setting_string_false_is_coerced_to_false():
    repo = DummySettingsRepository({"rss.enabled": "false"})
    settings = SettingsService(
        repo,
        settings_schema={
            "rss": {
                "enabled": {"type": "bool", "default": True, "label": "Enable RSS polling"},
            }
        },
        required_user_settings=set(),
    )

    assert settings.get("rss.enabled", default=True).value is False


def test_reader_theme_replaces_settings_page_theme_and_defaults_to_system():
    settings = SettingsService(
        DummySettingsRepository(),
        settings_schema=SETTINGS,
        user_settings_schema=USER_SETTINGS_SCHEMA,
        required_user_settings=REQUIRED_USER_SETTINGS,
    )

    assert "theme" not in SETTINGS["app"]
    assert "theme" not in USER_SETTINGS_SCHEMA
    assert settings.get_user_settings(1)["chapter_theme"] == "system"
    assert any(option["value"] == "system" for option in settings.get_reading_settings_schema()["theme"]["options"])
