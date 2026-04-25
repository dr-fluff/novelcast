# novelcast/pipeline/story_pipeline.py

class StoryPipeline:

    def __init__(self, engine, parser, db_writer, file_writer):
        self.engine = engine
        self.parser = parser
        self.db = db_writer
        self.files = file_writer

    def run(self, url: str):

        # STAGE 1
        download = self.engine.download_story(url)

        # STAGE 2
        story = self.parser.parse(download["file_path"])

        # STAGE 3
        story_id = self.db.save_story(story, url)

        self.db.save_chapters(story_id, story["chapters"])
        self.files.link_file(story_id, download["file_path"])

        return story_id