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
