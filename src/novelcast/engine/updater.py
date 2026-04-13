# src/novelcast/engine/updater.py

from pathlib import Path

class UpdateEngine:
    def __init__(self, db):
        self.db = db
        self.base = Path("data/stories")
        self.base.mkdir(parents=True, exist_ok=True)

    def check_updates(self):
        subs = self.db.get_subscriptions()

        for sub in subs:
            sub_id, url, title, last = sub

            print(f"Checking: {url}")

            # 🔥 Placeholder logic (replace with FanFicFare later)
            new_chapters = 0

            if new_chapters > 0:
                self.db.update_last_chapter(url, last + new_chapters)