# novelcast/services/settings_service.py

class SettingsService:
    def __init__(self, repo):
        self.repo = repo

    def get_server_setting(self, key: str, default=None):
        value = self.repo.get_server_setting(key)
        return value if value is not None else default

    def set_server_setting(self, key: str, value: str):
        return self.repo.set_server_setting(key, value)

    def get_server_settings(self):
        settings = self.repo.get_all_server_settings()
        if settings is None:
            return {}
        return settings

    def get_user_settings(self, user_id: int):
        settings = self.repo.get_user_settings(user_id)
        if settings:
            return settings

        return {
            "user_id": user_id,
            "theme": "light",
            "font_size": 14,
            "line_height": 1.5,
            "auto_update": 1,
        }

    def save_user_settings(self, user_id: int, theme: str, font_size: int, line_height: float, auto_update: int):
        return self.repo.save_user_settings(user_id, theme, font_size, line_height, auto_update)
