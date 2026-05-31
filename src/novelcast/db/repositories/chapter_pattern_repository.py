# novelcast/db/repositories/chapter_pattern_repository.py

import re

from sqlalchemy import select

from novelcast.db.repositories.base import BaseRepository
from novelcast.db.models.chapter_pattern import ChapterPattern


class ChapterPatternRepository(BaseRepository):

    # ── reads ──────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(ChapterPattern).order_by(ChapterPattern.id)
            ).all()
            return [_to_dict(r) for r in rows]

    def get_enabled(self) -> list[dict]:
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(ChapterPattern)
                .where(ChapterPattern.enabled == True)  # noqa: E712
                .order_by(ChapterPattern.id)
            ).all()
            return [_to_dict(r) for r in rows]

    def get_enabled_regexes(self) -> list[str]:
        """Convenience method — returns just the raw pattern strings."""
        return [p["pattern"] for p in self.get_enabled()]

    def get_by_id(self, pattern_id: int) -> dict | None:
        with self.session_no_commit() as db:
            return _to_dict(db.get(ChapterPattern, pattern_id))

    # ── writes ─────────────────────────────────────────────────────────────

    def create(self, pattern: str, description: str = "") -> int:
        _validate_regex(pattern)
        with self.session() as db:
            row = ChapterPattern(pattern=pattern, description=description)
            db.add(row)
            db.flush()
            return row.id

    def update(self, pattern_id: int, pattern: str, description: str) -> dict | None:
        _validate_regex(pattern)
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if not row:
                return None
            row.pattern = pattern
            row.description = description
            db.flush()
            return _to_dict(row)

    def set_enabled(self, pattern_id: int, enabled: bool) -> None:
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if row:
                row.enabled = enabled

    def delete(self, pattern_id: int) -> None:
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if row:
                db.delete(row)

    # ── test helper ────────────────────────────────────────────────────────

    def test_pattern(self, pattern: str, samples: list[str]) -> list[dict]:
        """
        Dry-run a pattern against sample titles without saving.
        Returns [{"title": str, "matches": bool}] for GUI preview.
        """
        _validate_regex(pattern)
        compiled = re.compile(pattern, re.IGNORECASE)
        return [{"title": t, "matches": bool(compiled.search(t))} for t in samples]


# ── helpers ────────────────────────────────────────────────────────────────

def _validate_regex(pattern: str) -> None:
    try:
        re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e


def _to_dict(row: ChapterPattern | None) -> dict | None:
    if row is None:
        return None
    return {
        "id":          row.id,
        "pattern":     row.pattern,
        "description": row.description,
        "enabled":     row.enabled,
        "created_at":  row.created_at,
    }