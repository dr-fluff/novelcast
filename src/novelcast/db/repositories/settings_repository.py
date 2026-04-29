# novelcast/db/repositories/settings_repository.py

from novelcast.db.query_manager import QueryManager
from novelcast.db.database import Database


class SettingsRepository:
    def __init__(self, db: Database, qm: QueryManager):
        self.db = db
        self.qm = qm

    def get_server_setting(self, key: str):
        row = self.db.fetchone(self.qm.sql("settings.get_server_setting"), (key,))
        return row["value"] if row else None

    def set_server_setting(self, key: str, value: str):
        return self.db.execute(self.qm.sql("settings.set_server_setting"), (key, value))

    def get_all_server_settings(self):
        rows = self.db.fetchall(self.qm.sql("settings.get_all"), ())
        return {row["key"]: row["value"] for row in rows}

    def get_user_settings(self, user_id: int):
        return self.db.fetchone(self.qm.sql("settings.get_user_settings"), (user_id,))

    def save_user_settings(self, user_id: int, theme: str, font_size: int, line_height: float, auto_update: int):
        return self.db.execute(
            self.qm.sql("settings.upsert_user_settings"),
            (user_id, theme, font_size, line_height, auto_update),
        )
