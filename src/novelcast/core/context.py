# novelcast/core/context.py
import logging
from queue import Queue

from novelcast.db.init_db import init_db
from novelcast.db.session import SessionLocal
from novelcast.db.engine import engine

from novelcast.db.repositories import (
    StoriesRepository,
    UsersRepository,
    FilesRepository,
    ChaptersRepository,
    ProgressRepository,
    SyncRepository,
    SettingsRepository,
    AuthorRepository,
)
from novelcast.db.repositories.chapter_pattern_repository import ChapterPatternRepository

from novelcast.services import (
    AuthService,
    ChaptersService,
    FileService,
    ProgressService,
    SettingsService,
    StoryService,
    UserService,
    FanFicFareConfigService,
    PatreonConfigService,
    StoryDownloadService,
    LibrarySyncService,
    RssService,
    HealthCheckService,
)
from novelcast.services.chapter_filter_service import ChapterFilterService

from novelcast.engine import (
    FanFicFareEngine,
    PatreonEngine,
    EngineSelector,
    StoryDownloadOrchestrator,
)

from novelcast.parser import (
    StoryParser,
    EpubParser,
    FanFicFareParser,
    HtmlParser,
    ParserRegistry,
    PatreonParser
)

from novelcast.rss import (
    RoyalRoadRss
)

from novelcast.pipeline.story_pipeline import StoryPipeline
from novelcast.utils.files import FileUtils
from novelcast.core.defaults import SETTINGS

logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self, app_config):
        logger.info("Starting AppContext initialization")

        self.app_config = app_config
        self.event_queue = Queue()
        self.ws_manager = None

        self._init_database()
        self._init_repositories()
        self._init_services()
        self._init_engine_config()
        self._init_utils()
        self._init_engine()
        self._init_parser_registry()
        self._init_parser()
        self._init_pipeline()
        self._init_orchestrator()
        self._init_service_layer()
        self._init_rss()
        self._validate()
        

        logger.info("AppContext ready")

    # ─────────────────────────────
    # EVENTS
    # ─────────────────────────────
    def emit(self, event_type: str, payload: dict):
        if not self.ws_manager:
            return
        self.event_queue.put((event_type, payload))

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    def _init_database(self):
        logger.info("Initializing database...")
        init_db()
        self.SessionLocal = SessionLocal
        self.engine = engine

    def get_db(self):
        return self.SessionLocal()

    # ─────────────────────────────
    # REPOSITORIES
    # ─────────────────────────────
    def _init_repositories(self):
        logger.info("Initializing repositories...")

        sf = self.SessionLocal

        self.stories_repo          = StoriesRepository(sf)
        self.authors_repo          = AuthorRepository(sf)
        self.users_repo            = UsersRepository(sf)
        self.files_repo            = FilesRepository(sf)
        self.chapters_repo         = ChaptersRepository(sf)
        self.progress_repo         = ProgressRepository(sf)
        self.sync_repo             = SyncRepository(self.chapters_repo)
        self.settings_repo         = SettingsRepository(sf)
        self.chapter_pattern_repo  = ChapterPatternRepository(sf)  # ← new

    # ─────────────────────────────
    # SERVICES (business logic)
    # ─────────────────────────────
    def _init_services(self):
        logger.info("Initializing services...")

        self.stories  = StoryService(self.stories_repo, author_repo=self.authors_repo)
        self.users    = UserService(self.users_repo)
        self.auth     = AuthService(self.users_repo)
        self.files    = FileService(self.files_repo)
        self.chapters = ChaptersService(self.chapters_repo)
        self.progress = ProgressService(self.progress_repo)

        self.settings = SettingsService(
            self.settings_repo,
            settings_schema=SETTINGS,
            secret_key=self.app_config.secret_key,
        )
        self.settings.migrate_server_secrets()

        self.chapter_filter = ChapterFilterService(self.chapter_pattern_repo)

        # Resolve stories_dir from settings — adjust the key path to match
        # wherever your storage path lives in your SETTINGS schema.
        server_settings = self.settings.get_resolved_server_settings()
        stories_dir: str | None = (
            server_settings.get("storage", {}).get("stories_dir")
            or server_settings.get("library", {}).get("stories_dir")
            or None
        )

        self.health_check = HealthCheckService(
            session_factory=self.SessionLocal,
            stories_dir=stories_dir,
        )

    # ─────────────────────────────
    # ENGINE CONFIG (writers)
    # ─────────────────────────────
    def _init_engine_config(self):
        logger.info("Initializing engine config...")

        self.engines_config = {
            "fanficfare": {
                "prefix": "fanficfare.",
                "writer": FanFicFareConfigService(self.settings),
            },
            "patreon": {
                "prefix": "patreon.",
                "writer": PatreonConfigService(self.settings),
            },
        }

        for cfg in self.engines_config.values():
            cfg["writer"].write_config(force=True)

        self.settings_repo.on_change = self._on_settings_change

    def _on_settings_change(self, key: str):
        for cfg in self.engines_config.values():
            if key.startswith(cfg["prefix"]):
                cfg["writer"].write_config(force=False)
                return

    # ─────────────────────────────
    # UTILS
    # ─────────────────────────────
    def _init_utils(self):
        self.file_utils = FileUtils()

    # ─────────────────────────────
    # ENGINE (fetch only)
    # ─────────────────────────────
    def _init_engine(self):
        logger.info("Initializing engines...")

        self.fanficfare_engine = FanFicFareEngine(
            self.settings_repo,
            self.engines_config["fanficfare"]["writer"],
        )

        self.patreon_engine = PatreonEngine(
            self.settings_repo,
            self.engines_config["patreon"]["writer"],
        )

        self.engine_selector = EngineSelector([
            self.fanficfare_engine,
            self.patreon_engine,
        ])

    # ─────────────────────────────
    # PARSER REGISTRY
    # ─────────────────────────────
    def _init_parser_registry(self):
        patterns = self.chapter_filter.get_enabled_regexes()

        self.epub_parser = EpubParser(patterns=patterns)

        self.parser_registry = ParserRegistry(
            {
                "fanficfare": FanFicFareParser(),
                "html": HtmlParser(),
                "epub": self.epub_parser,
                "patreon": PatreonParser(),
            }
        )
    # ─────────────────────────────
    # PARSER
    # ─────────────────────────────
    def _init_parser(self):
        self.story_parser = StoryParser(self.parser_registry)

    # ─────────────────────────────
    # PIPELINE (DB + filesystem persistence)
    # ─────────────────────────────
    def _init_pipeline(self):
        logger.info("Initializing pipeline...")

        self.story_pipeline = StoryPipeline(
            stories_repo=self.stories_repo,
            chapters_repo=self.chapters_repo,
            file_utils=self.file_utils,
            epub_parser=self.epub_parser,
        )
    
    def _init_rss(self):
        logger.info("Initializing RSS")

        self.rss_service = RssService(readers=[
            RoyalRoadRss(self.stories),
        ])
        
    # ─────────────────────────────
    # ORCHESTRATOR (engine coordination only)
    # ─────────────────────────────
    def _init_orchestrator(self):
        logger.info("Initializing orchestrator...")

        self.story_orchestrator = StoryDownloadOrchestrator(
            selector=self.engine_selector,
        )

    # ─────────────────────────────
    # SERVICE LAYER (API entrypoint)
    # ─────────────────────────────
    def _init_service_layer(self):
        logger.info("Initializing story download service...")

        self.story_download = StoryDownloadService(
            orchestrator=self.story_orchestrator,
            pipeline=self.story_pipeline,
            parser=self.story_parser,
            stories_repo=self.stories_repo,
            notifier=self.emit,
        )

        self.library_sync = LibrarySyncService(
            stories=self.stories,
            download=self.story_download,
            settings=self.settings,
            notifier=self.emit,
        )

    # ─────────────────────────────
    # VALIDATION
    # ─────────────────────────────
    def _validate(self):
        required = [
            "SessionLocal",
            "stories_repo",
            "users_repo",
            "story_download",
            "parser_registry",
            "story_parser",
            "engine_selector",
            "story_pipeline",
            "chapter_filter",       
            "chapter_pattern_repo",
            "health_check", 
        ]

        for r in required:
            if not hasattr(self, r):
                raise RuntimeError(f"Missing AppContext attr: {r}")