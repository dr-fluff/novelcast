from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from novelcast.db.base import Base
from novelcast.db.models.chapter import Chapter, ChapterFile
from novelcast.db.models.story import Story
from novelcast.db.repositories.chapters_repository import ChaptersRepository


def test_upsert_same_chapter_does_not_duplicate_file_records(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = ChaptersRepository(Session)

    try:
        with Session() as db:
            story = Story(
                title="Test story",
                story_site_id="test-story-1",
                source_url="https://example.com/story",
            )
            db.add(story)
            db.commit()
            story_id = story.id

        chapter_url = "https://example.com/story/chapter/123"
        chapter_path = tmp_path / "001_Test.html"
        chapter_path.write_text("Test chapter content", encoding="utf-8")

        for _ in range(2):
            repo.upsert(
                story_id,
                1,
                "Chapter 1",
                chapter_url,
                str(chapter_path),
                1,
            )

        with Session() as db:
            chapters = db.scalars(
                select(Chapter).where(Chapter.story_id == story_id)
            ).all()
            files = db.scalars(select(ChapterFile)).all()

            assert len(chapters) == 1
            assert len(files) == 1
            assert files[0].chapter_id == chapters[0].id
            assert files[0].is_canonical is True

            original_chapter_id = chapters[0].id
            original_file_id = files[0].id

        repo.upsert(
            story_id,
            1,
            "Updated Chapter 1",
            chapter_url,
            str(chapter_path),
            1,
        )

        with Session() as db:
            chapter = db.get(Chapter, original_chapter_id)
            files = db.scalars(
                select(ChapterFile).where(
                    ChapterFile.chapter_id == original_chapter_id
                )
            ).all()

            assert chapter is not None
            assert chapter.title == "Updated Chapter 1"
            assert len(files) == 1
            assert files[0].id == original_file_id

    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_upsert_does_not_move_chapter_on_url_conflict(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    repo = ChaptersRepository(Session)

    try:
        with Session() as db:
            story_a = Story(
                title="Story A",
                story_site_id="story-a",
                source_url="https://example.com/story-a",
            )
            story_b = Story(
                title="Story B",
                story_site_id="story-b",
                source_url="https://example.com/story-b",
            )
            db.add_all([story_a, story_b])
            db.commit()
            story_a_id = story_a.id
            story_b_id = story_b.id

        chapter_url = "https://example.com/shared/chapter/123"
        chapter_path = tmp_path / "001_Test.html"
        chapter_path.write_text("Test chapter content", encoding="utf-8")

        repo.upsert(
            story_a_id,
            1,
            "Chapter 1",
            chapter_url,
            str(chapter_path),
            1,
        )

        repo.upsert(
            story_b_id,
            1,
            "Chapter 1 in Story B",
            chapter_url,
            str(chapter_path),
            1,
        )

        with Session() as db:
            chapters = db.scalars(
                select(Chapter).where(Chapter.url == chapter_url)
            ).all()

            assert len(chapters) == 1
            assert chapters[0].story_id == story_a_id
            assert chapters[0].title == "Chapter 1"

    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()