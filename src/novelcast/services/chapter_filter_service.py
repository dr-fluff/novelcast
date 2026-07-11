# novelcast/services/chapter_filter_service.py

from novelcast.db.repositories.chapter_pattern_repository import (
    ChapterPatternRepository,
)


class ChapterFilterService:
    """
    Thin service layer over ChapterPatternRepository.
    Used by StoryDownloadService to push DB patterns into EpubParser,
    and by the settings API/GUI to manage patterns.
    """

    def __init__(self, chapter_pattern_repo: ChapterPatternRepository):
        self.repo = chapter_pattern_repo

    def get_all_patterns(self) -> list[dict]:
        return self.repo.get_all()

    def get_enabled_regexes(self) -> list[str]:
        return self.repo.get_enabled_regexes()

    def add_pattern(self, pattern: str, description: str = "") -> dict:
        pattern_id = self.repo.create(pattern, description)
        return self.repo.get_by_id(pattern_id)

    def update_pattern(self, pattern_id: int, pattern: str, description: str) -> dict | None:
        return self.repo.update(pattern_id, pattern, description)

    def set_enabled(self, pattern_id: int, enabled: bool) -> None:
        self.repo.set_enabled(pattern_id, enabled)

    def delete_pattern(self, pattern_id: int) -> None:
        self.repo.delete(pattern_id)

    def test_pattern(self, pattern: str, samples: list[str]) -> list[dict]:
        """Preview matches before saving. Safe — does not touch the DB."""
        return self.repo.test_pattern(pattern, samples)
