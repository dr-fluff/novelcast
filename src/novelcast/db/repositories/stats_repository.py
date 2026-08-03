# novelcast/db/repositories/stats_repository.py

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import aliased

from novelcast.db.models.chapter import Chapter
from novelcast.db.models.progress import ReadingProgress
from novelcast.db.models.stats import UserDailyActivity, UserDevice
from novelcast.db.repositories.base import BaseRepository


class StatsRepository(BaseRepository):
    # ── read time / heartbeat ───────────────────────────────────────────

    def record_heartbeat(self, user_id: int, seconds: int, on: date | None = None) -> None:
        """Adds `seconds` to today's (UTC) read_seconds for this user,
        creating the day's row if it doesn't exist yet. `on` is exposed
        for tests; callers should normally omit it and let it default
        to today."""
        activity_date = on or datetime.now(timezone.utc).date()
        with self.session() as db:
            stmt = (
                insert(UserDailyActivity)
                .values(
                    user_id=user_id,
                    activity_date=activity_date,
                    read_seconds=seconds,
                )
                .on_conflict_do_update(
                    index_elements=["user_id", "activity_date"],
                    set_={
                        "read_seconds": UserDailyActivity.read_seconds + seconds,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )
            )
            db.execute(stmt)

    def get_total_read_seconds(self, user_id: int) -> int:
        with self.session_no_commit() as db:
            total = db.scalar(
                select(func.coalesce(func.sum(UserDailyActivity.read_seconds), 0)).where(
                    UserDailyActivity.user_id == user_id
                )
            )
            return total or 0

    def get_activity_heatmap(self, user_id: int, days: int = 365) -> list[dict]:
        """Returns one dict per active day in the last `days` days:
        {"date": date, "read_seconds": int}. Days with no activity simply
        don't appear — the caller fills gaps for display."""
        since = datetime.now(timezone.utc).date() - timedelta(days=days)
        with self.session_no_commit() as db:
            rows = db.execute(
                select(UserDailyActivity.activity_date, UserDailyActivity.read_seconds)
                .where(
                    UserDailyActivity.user_id == user_id,
                    UserDailyActivity.activity_date >= since,
                )
                .order_by(UserDailyActivity.activity_date)
            ).all()
            return [{"date": activity_date, "read_seconds": read_seconds} for activity_date, read_seconds in rows]

    # ── devices ──────────────────────────────────────────────────────────

    def touch_device(self, user_id: int, device_id: str, label: str | None = None) -> None:
        """Upserts a (user, device) row: creates it with first_seen_at on
        first sight, otherwise just bumps last_seen_at. `label` only
        overwrites an existing value when explicitly provided."""
        with self.session() as db:
            values = {"user_id": user_id, "device_id": device_id}
            if label is not None:
                values["label"] = label

            update_set = {"last_seen_at": datetime.now(timezone.utc)}
            if label is not None:
                update_set["label"] = label

            stmt = (
                insert(UserDevice)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["user_id", "device_id"],
                    set_=update_set,
                )
            )
            db.execute(stmt)

    def get_device_count(self, user_id: int) -> int:
        with self.session_no_commit() as db:
            return db.scalar(
                select(func.count()).select_from(UserDevice).where(UserDevice.user_id == user_id)
            ) or 0

    # ── derived: chapters / stories read, reading speed ────────────────

    def get_chapters_read(self, user_id: int) -> int:
        """Sum of furthest chapter_number reached across all stories.
        Assumes chapter_number is contiguous from 1 per story, so
        "furthest chapter_number" == "chapters read" for that story."""
        FurthestChapter = aliased(Chapter)
        with self.session_no_commit() as db:
            total = db.scalar(
                select(func.coalesce(func.sum(FurthestChapter.chapter_number), 0))
                .select_from(ReadingProgress)
                .join(FurthestChapter, FurthestChapter.id == ReadingProgress.furthest_chapter_id)
                .where(ReadingProgress.user_id == user_id)
            )
            return total or 0

    def get_stories_read(self, user_id: int) -> int:
        with self.session_no_commit() as db:
            return db.scalar(
                select(func.count())
                .select_from(ReadingProgress)
                .where(
                    ReadingProgress.user_id == user_id,
                    ReadingProgress.furthest_chapter_id.is_not(None),
                )
            ) or 0

    def get_words_read(self, user_id: int) -> int:
        """Sum of word_count for every chapter at or before the furthest
        chapter reached, per story. Chapters with a NULL word_count (not
        yet computed) contribute 0 rather than breaking the sum."""
        FurthestChapter = aliased(Chapter)
        with self.session_no_commit() as db:
            per_story_words = (
                select(func.coalesce(func.sum(Chapter.word_count), 0))
                .where(
                    Chapter.story_id == ReadingProgress.story_id,
                    Chapter.chapter_number <= FurthestChapter.chapter_number,
                )
                .correlate(ReadingProgress, FurthestChapter)
                .scalar_subquery()
            )
            total = db.scalar(
                select(func.coalesce(func.sum(per_story_words), 0))
                .select_from(ReadingProgress)
                .join(FurthestChapter, FurthestChapter.id == ReadingProgress.furthest_chapter_id)
                .where(ReadingProgress.user_id == user_id)
            )
            return total or 0

    def get_reading_speed_wpm(self, user_id: int) -> float | None:
        """Words per minute, or None if there's not enough data yet
        (no read time recorded) to avoid a division by zero / misleading 0."""
        total_seconds = self.get_total_read_seconds(user_id)
        if total_seconds <= 0:
            return None
        words = self.get_words_read(user_id)
        return words / (total_seconds / 60)