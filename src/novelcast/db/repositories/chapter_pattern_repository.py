# novelcast/db/repositories/chapter_pattern_repository.py

import re

from sqlalchemy import select

from novelcast.db.models.chapter_pattern import ChapterPattern
from novelcast.db.repositories.base import BaseRepository


class ChapterPatternRepository(BaseRepository):
    """Repository for chapter pattern management."""

    def get_all(self) -> list[dict]:
        """Return all patterns with metadata."""
        with self.session_no_commit() as db:
            rows = db.scalars(select(ChapterPattern).order_by(ChapterPattern.id)).all()
            return [
                {
                    "id": row.id,
                    "pattern": row.pattern,
                    "description": row.description,
                    "enabled": row.enabled,
                    "is_builtin": row.is_builtin,
                }
                for row in rows
            ]

    def get_enabled_regexes(self) -> list[str]:
        """Return only enabled patterns as regex strings (for EpubParser)."""
        with self.session_no_commit() as db:
            rows = db.scalars(
                select(ChapterPattern).where(ChapterPattern.enabled).order_by(ChapterPattern.id)
            ).all()
            return [row.pattern for row in rows]

    def get_by_id(self, pattern_id: int) -> dict | None:
        """Get a single pattern by ID."""
        with self.session_no_commit() as db:
            row = db.get(ChapterPattern, pattern_id)
            if not row:
                return None
            return {
                "id": row.id,
                "pattern": row.pattern,
                "description": row.description,
                "enabled": row.enabled,
                "is_builtin": row.is_builtin,
            }

    def create(self, pattern: str, description: str = "") -> int:
        """Add a new custom pattern. Returns the pattern ID."""
        with self.session() as db:
            p = ChapterPattern(
                pattern=pattern,
                description=description,
                enabled=True,
                is_builtin=False,
            )
            db.add(p)
            db.flush()
            pattern_id = p.id
        return pattern_id

    def update(self, pattern_id: int, pattern: str, description: str) -> dict | None:
        """Update a pattern. Returns updated pattern dict."""
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if not row:
                return None

            row.pattern = pattern
            row.description = description
            db.flush()

            return {
                "id": row.id,
                "pattern": row.pattern,
                "description": row.description,
                "enabled": row.enabled,
                "is_builtin": row.is_builtin,
            }

    def set_enabled(self, pattern_id: int, enabled: bool) -> None:
        """Toggle pattern enabled/disabled."""
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if row:
                row.enabled = enabled

    def delete(self, pattern_id: int) -> None:
        """Delete a custom pattern (not builtin)."""
        with self.session() as db:
            row = db.get(ChapterPattern, pattern_id)
            if row and not row.is_builtin:
                db.delete(row)

    def seed_defaults(self, default_patterns: dict[str, str]) -> None:
        with self.session() as db:
            existing_patterns = set(db.scalars(select(ChapterPattern.pattern)).all())
            added = 0
            for pattern, description in default_patterns.items():
                if pattern in existing_patterns:
                    continue
                db.add(
                    ChapterPattern(
                        pattern=pattern,
                        description=description,
                        enabled=True,
                        is_builtin=True,
                    )
                )
                added += 1

            return added

    def test_pattern(self, pattern: str, samples: list[str]) -> list[dict]:
        """
        Test a regex pattern against sample titles.
        Safe — does not touch the DB.

        Returns: list of {sample, matched}
        """
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return [{"error": str(e)}]

        results = []
        for sample in samples:
            match = compiled.search(sample)
            results.append(
                {
                    "sample": sample,
                    "matched": bool(match),
                    "groups": match.groups() if match else None,
                }
            )
        return results
