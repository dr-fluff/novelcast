# novelcast/db/repositories/settings_repository.py

from novelcast.db.query_manager import QueryManager
from novelcast.db.database import Database

import json

class SettingsRepository:
    def __init__(self, db: Database, qm: QueryManager):
        self.db = db
        self.qm = qm

    def _deserialize(self, value):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value  # fallback safety

    def get_server_setting(self, key: str):
        row = self.db.fetchone(self.qm.sql("settings.get_server_setting"), (key,))
        return self._deserialize(row["value"]) if row else None

    def get_all_server_settings(self):
        rows = self.db.fetchall(self.qm.sql("settings.get_all"), ())
        return {
            row["key"]: self._deserialize(row["value"])
            for row in rows
        }

    def set_server_setting(self, key: str, value):
        import json
        return self.db.execute(
            self.qm.sql("settings.set_server_setting"),
            (key, json.dumps(value)),
        )
    
    def get_user_settings(self, user_id: int):
        return self.db.fetchone(
            self.qm.sql("settings.get_user_settings"),
            (user_id,),
        )


    def save_user_settings(
        self,
        user_id: int,
        theme: str,
        font_size: int,
        line_height: float,
        auto_update: int,
    ):
        return self.db.execute(
            self.qm.sql("settings.upsert_user_settings"),
            (user_id, theme, font_size, line_height, auto_update),
        )