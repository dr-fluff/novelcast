# novelcast/pipeline/story_pipeline.py
from pathlib import Path

class StoryPipeline:

    def __init__(self, stories_repo, chapters_repo, file_utils):
        self.stories_repo = stories_repo
        self.chapters_repo = chapters_repo
        self.file_utils = file_utils

    def persist(self, story: dict):
        story_id = self.stories_repo.create(
            story["title"],
            story.get("author"),
            story.get("source_url") or story.get("url")
        )

        base_dir = self.file_utils.story_dir(
            story.get("author"),
            story.get("title")
        )

        cover_path = self._persist_cover(base_dir, story)

        epub_source_path = story.get("source_file_path")
        if epub_source_path:
            epub_source = Path(epub_source_path)
            if epub_source.exists():
                epub_dest = base_dir / self.file_utils.safe(epub_source.name)
                epub_source.replace(epub_dest)

        self.stories_repo.update_paths(
            story_id,
            str(base_dir),
            str(cover_path) if cover_path else None,
        )

        story_url = story.get("source_url") or story.get("url") or ""
        chapter_numbers = []

        for ch in story["chapters"]:
            title_safe = self.file_utils.safe(ch.get("title") or "")
            filename = f"{ch['number']:03d}_{title_safe or f'chapter_{ch['number']:03d}'}.html"

            path = self.file_utils.write_chapter(
                base_dir,
                filename,
                ch["content"]
            )

            chapter_numbers.append(ch["number"])
            chapter_url = f"{story_url}#chapter-{ch['number']}" if story_url else f"file://{str(path)}"
            self.chapters_repo.upsert(
                story_id,
                ch["number"],
                ch.get("title"),
                chapter_url,
                str(path),
                1,
            )

        total_chapters = len(chapter_numbers)
        latest_downloaded = max(chapter_numbers) if chapter_numbers else None
        self.stories_repo.update_chapter_stats(
            story_id,
            total_chapters,
            total_chapters,
            latest_downloaded,
            total_chapters,
            total_chapters,
        )

        return story_id
    
    def append_new_chapters(self, story_id: int, story: dict):
        base_dir = self.file_utils.story_dir(
            story.get("author"),
            story.get("title")
        )

        story_url = story.get("source_url") or story.get("url") or ""

        existing = self.chapters_repo.get_numbers(story_id)
        existing_set = set(existing)

        new_chapter_numbers = []

        for ch in story["chapters"]:
            if ch["number"] in existing_set:
                continue

            title_safe = self.file_utils.safe(ch.get("title") or "")
            filename = f"{ch['number']:03d}_{title_safe or f'chapter_{ch['number']:03d}'}.html"

            path = self.file_utils.write_chapter(
                base_dir,
                filename,
                ch["content"]
            )

            chapter_url = (
                f"{story_url}#chapter-{ch['number']}"
                if story_url else f"file://{str(path)}"
            )

            self.chapters_repo.upsert(
                story_id,
                ch["number"],
                ch.get("title"),
                chapter_url,
                str(path),
                1,
            )

            new_chapter_numbers.append(ch["number"])

        return new_chapter_numbers