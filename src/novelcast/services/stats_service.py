# novelcast/services/stats_service.py


class StatsService:
    def __init__(self, repo):
        self.repo = repo

    # ── read time / heartbeat ───────────────────────────────────────────

    def record_heartbeat(self, user_id: int, seconds: int) -> None:
        self.repo.record_heartbeat(user_id, seconds)

    def get_total_read_seconds(self, user_id: int) -> int:
        return self.repo.get_total_read_seconds(user_id)

    def get_activity_heatmap(self, user_id: int, days: int = 365) -> list[dict]:
        return self.repo.get_activity_heatmap(user_id, days)

    # ── devices ──────────────────────────────────────────────────────────

    def touch_device(self, user_id: int, device_id: str, label: str | None = None) -> None:
        self.repo.touch_device(user_id, device_id, label)

    def get_device_count(self, user_id: int) -> int:
        return self.repo.get_device_count(user_id)

    # ── derived stats ────────────────────────────────────────────────────

    def get_chapters_read(self, user_id: int) -> int:
        return self.repo.get_chapters_read(user_id)

    def get_stories_read(self, user_id: int) -> int:
        return self.repo.get_stories_read(user_id)

    def get_words_read(self, user_id: int) -> int:
        return self.repo.get_words_read(user_id)

    def get_reading_speed_wpm(self, user_id: int) -> float | None:
        return self.repo.get_reading_speed_wpm(user_id)

    def get_summary(self, user_id: int) -> dict:
        """Convenience bundle for a stats/profile page — one call instead
        of five, since these are typically all shown together."""
        return {
            "total_read_seconds": self.get_total_read_seconds(user_id),
            "device_count": self.get_device_count(user_id),
            "chapters_read": self.get_chapters_read(user_id),
            "stories_read": self.get_stories_read(user_id),
            "reading_speed_wpm": self.get_reading_speed_wpm(user_id),
        }
