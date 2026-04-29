import logging

from novelcast.db.database import Database
from novelcast.db.query_manager import QueryManager

from novelcast.db.repositories.stories_repository import StoriesRepository
from novelcast.db.repositories.users_repository import UsersRepository
from novelcast.db.repositories.files_repository import FilesRepository
from novelcast.db.repositories.chapters_repository import ChaptersRepository
from novelcast.db.repositories.progress_repository import ProgressRepository
from novelcast.db.repositories.sync_repository import SyncRepository
from novelcast.db.repositories.settings_repository import SettingsRepository

from novelcast.services.story_service import StoryService
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService
from novelcast.services.file_service import FileService
from novelcast.services.page_service import PageService
from novelcast.services.chapters_service import ChaptersService
from novelcast.services.progress_service import ProgressService
from novelcast.services.story_download_service import StoryDownloadService
from novelcast.services.settings_service import SettingsService

from novelcast.engine.fanficfare_engine import FanFicFareEngine
from novelcast.engine.engine_selector import EngineSelector

from novelcast.parser.story_parser import StoryParser
from novelcast.parser.epub_parser import EpubParser
from novelcast.parser.fanficfare_parser import FanFicFareParser
from novelcast.parser.html_parser import HtmlParser
from novelcast.parser.registry import ParserRegistry

from novelcast.pipeline.story_pipeline import StoryPipeline
from novelcast.utils.files import FileUtils

logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self):
        logger.info("Starting AppContext initialization")

        self._init_database()
        self._init_repositories()
        self._init_services()
        self._init_utils()
        self._init_engine()

        # IMPORTANT: registry must exist BEFORE parser
        self._init_parser_registry()
        self._init_parser()

        self._init_pipeline()
        self._init_orchestration()

        self._validate()

        logger.info("AppContext ready")

    # -------------------------
    # DATABASE
    # -------------------------
    def _init_database(self):
        try:
            logger.info("Initializing database...")
            self.db = Database()
            self.db.init_schema()
            self.qm = QueryManager(self.db)
        except Exception as e:
            logger.exception("Database initialization failed")
            raise RuntimeError("Database layer failed") from e

    # -------------------------
    # REPOSITORIES
    # -------------------------
    def _init_repositories(self):
        try:
            logger.info("Initializing repositories...")
            self.stories_repo = StoriesRepository(self.db)
            self.users_repo = UsersRepository(self.db)
            self.files_repo = FilesRepository(self.db)
            self.chapters_repo = ChaptersRepository(self.db)
            self.progress_repo = ProgressRepository(self.qm)
            self.sync_repo = SyncRepository(self.chapters_repo)
            self.settings_repo = SettingsRepository(self.db, self.qm)
        except Exception as e:
            logger.exception("Repository initialization failed")
            raise RuntimeError("Repository layer failed") from e

    # -------------------------
    # SERVICES
    # -------------------------
    def _init_services(self):
        try:
            logger.info("Initializing services...")
            self.stories = StoryService(self.stories_repo)
            self.users = UserService(self.users_repo)
            self.auth = AuthService(self.users_repo)
            self.files = FileService(self.files_repo)
            self.pages = PageService(self.stories_repo)
            self.chapters = ChaptersService(self.chapters_repo)
            self.progress = ProgressService(self.progress_repo)
            self.settings = SettingsService(self.settings_repo)
        except Exception as e:
            logger.exception("Service initialization failed")
            raise RuntimeError("Service layer failed") from e

    # -------------------------
    # UTILS
    # -------------------------
    def _init_utils(self):
        try:
            logger.info("Initializing file utilities...")
            self.file_utils = FileUtils()
        except Exception as e:
            logger.exception("FileUtils initialization failed")
            raise RuntimeError("File utils failed") from e

    # -------------------------
    # ENGINE
    # -------------------------
    def _init_engine(self):
        try:
            logger.info("Initializing engine layer...")
            self.fanficfare_engine = FanFicFareEngine()

            self.engine_selector = EngineSelector(
                fanficfare_engine=self.fanficfare_engine
            )

        except Exception as e:
            logger.exception("Engine initialization failed")
            raise RuntimeError("Engine layer failed") from e

    # -------------------------
    # PARSER REGISTRY
    # -------------------------
    def _init_parser_registry(self):
        try:
            logger.info("Initializing parser registry...")

            self.parser_registry = ParserRegistry()

            # register parsers
            self.parser_registry.register("fanficfare", FanFicFareParser())
            self.parser_registry.register("epub", EpubParser())
            self.parser_registry.register("html", HtmlParser())

        except Exception as e:
            logger.exception("Parser registry initialization failed")
            raise RuntimeError("Parser registry failed") from e

    # -------------------------
    # PARSER (dispatcher)
    # -------------------------
    def _init_parser(self):
        try:
            logger.info("Initializing parser...")

            self.story_parser = StoryParser(
                registry=self.parser_registry
            )

        except Exception as e:
            logger.exception("Parser initialization failed")
            raise RuntimeError("Parser layer failed") from e

    # -------------------------
    # PIPELINE
    # -------------------------
    def _init_pipeline(self):
        try:
            logger.info("Initializing pipeline...")

            self.story_pipeline = StoryPipeline(
                stories_repo=self.stories_repo,
                chapters_repo=self.chapters_repo,
                file_utils=self.file_utils,
            )

        except Exception as e:
            logger.exception("Pipeline initialization failed")
            raise RuntimeError("Pipeline layer failed") from e

    # -------------------------
    # ORCHESTRATION
    # -------------------------
    def _init_orchestration(self):
        try:
            logger.info("Initializing StoryDownloadService...")

            self.story_download = StoryDownloadService(
                selector=self.engine_selector,
                parser=self.story_parser,
                pipeline=self.story_pipeline,
            )

        except Exception as e:
            logger.exception(
                "StoryDownloadService initialization failed",
                extra={
                    "selector": type(self.engine_selector).__name__,
                    "parser": type(self.story_parser).__name__,
                },
            )
            raise RuntimeError("Orchestration layer failed") from e

    # -------------------------
    # VALIDATION
    # -------------------------
    def _validate(self):
        logger.debug("Validating AppContext...")

        required_attrs = [
            "db",
            "stories_repo",
            "users_repo",
            "story_download",
            "parser_registry",
            "story_parser",
        ]

        for attr in required_attrs:
            if getattr(self, attr, None) is None:
                raise RuntimeError(f"AppContext validation failed: {attr} is missing")