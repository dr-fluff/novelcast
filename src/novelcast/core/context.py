# novelcast/core/context.py

import logging

from novelcast.db.database import Database
from novelcast.db.query_manager import QueryManager

from novelcast.db.repositories.stories_repository import StoriesRepository
from novelcast.db.repositories.users_repository import UsersRepository
from novelcast.db.repositories.files_repository import FilesRepository
from novelcast.db.repositories.chapters_repository import ChaptersRepository
from novelcast.db.repositories.sync_repository import SyncRepository

from novelcast.services.story_service import StoryService
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService
from novelcast.services.file_service import FileService
from novelcast.services.page_service import PageService
from novelcast.services.story_download_service import StoryDownloadService

from novelcast.engine.fanficfare_engine import FanFicFareEngine
from novelcast.engine.engine_selector import EngineSelector

from novelcast.parser.story_parser import StoryParser

from novelcast.pipeline.story_pipeline import StoryPipeline

from novelcast.utils.files import FileUtils

logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self):
        try:
            # -------------------------
            # DATABASE
            # -------------------------
            logger.info("Initializing database...")
            self.db = Database()
            self.db.init_schema()

            self.qm = QueryManager(self.db)

            # -------------------------
            # REPOSITORIES
            # -------------------------
            self.stories_repo = StoriesRepository(self.db)
            self.users_repo = UsersRepository(self.db)
            self.files_repo = FilesRepository(self.db)
            self.chapters_repo = ChaptersRepository(self.db)
            self.sync_repo = SyncRepository(self.chapters_repo)

            # -------------------------
            # SERVICES (simple domain services)
            # -------------------------
            self.stories = StoryService(self.stories_repo)
            self.users = UserService(self.users_repo)
            self.auth = AuthService(self.users_repo)
            self.files = FileService(self.files_repo)
            self.pages = PageService(self.stories_repo)

            # -------------------------
            # FILE UTILS
            # -------------------------
            self.file_utils = FileUtils()

            # -------------------------
            # ENGINE LAYER (FETCH)
            # -------------------------
            self.fanficfare_engine = FanFicFareEngine()

            self.engine_selector = EngineSelector(
                fanficfare_engine=self.fanficfare_engine
            )

            # -------------------------
            # PARSER LAYER (TRANSFORM)
            # -------------------------
            self.story_parser = StoryParser()

            # -------------------------
            # PIPELINE LAYER (PERSIST)
            # -------------------------
            self.story_pipeline = StoryPipeline(
                stories_repo=self.stories_repo,
                chapters_repo=self.chapters_repo,
                file_utils=self.file_utils,
            )

            # -------------------------
            # ORCHESTRATION SERVICE
            # -------------------------
            self.story_download = StoryDownloadService(
                selector=self.engine_selector,
                parser=self.story_parser,
                pipeline=self.story_pipeline,
            )

            logger.info("AppContext ready")

        except Exception:
            logger.exception("Fatal error in AppContext initialization")
            raise