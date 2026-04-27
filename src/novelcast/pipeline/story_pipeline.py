# novelcast/pipeline/story_pipeline.py
class StoryPipeline:

    def __init__(self, stories_repo, chapters_repo, file_utils):
        self.stories_repo = stories_repo
        self.chapters_repo = chapters_repo
        self.file_utils = file_utils

    def persist(self, story: dict):
        story_id = self.stories_repo.create(story)

        base_dir = self.file_utils.story_dir(
            story["author"],
            story["title"]
        )

        chapter_paths = []

        for ch in story["chapters"]:
            filename = f"chapter_{ch['number']}.html"

            path = self.file_utils.write_chapter(
                base_dir,
                filename,
                ch["content"]
            )

            chapter_paths.append(str(path))

            self.chapters_repo.create({
                "story_id": story_id,
                "number": ch["number"],
                "title": ch["title"],
                "file_path": str(path)
            })

        return story_id