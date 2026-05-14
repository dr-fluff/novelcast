# novelcast/core/context.py

import logging

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
)

from novelcast.services import (
    AuthService,
    ChaptersService,
    FanFicFareConfigService,
    FileService,
    ProgressService,
    SettingsService,
    StoryDownloadService,
    StoryService,
    UserService,
)

from novelcast.engine import (
    FanFicFareEngine,
    EngineSelector,
)

from novelcast.parser import (
    StoryParser,
    EpubParser,
    FanFicFareParser,
    HtmlParser,
    ParserRegistry
)

from novelcast.pipeline.story_pipeline import StoryPipeline
from novelcast.utils.files import FileUtils
from novelcast.core.defaults import SETTINGS

logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self, app_config):
        logger.info("Starting AppContext initialization")

        self.ws_manager = None  # injected later

        self._init_database()
        self._init_repositories()
        self._init_services()
        self._init_fanficfare_config()
        self._init_utils()
        self._init_engine()
        self._init_parser_registry()
        self._init_parser()
        self._init_pipeline()
        self._init_orchestration()
        self._validate()

        logger.info("AppContext ready")

    # ─────────────────────────────
    # EVENTS
    # ─────────────────────────────
    def emit(self, event_type: str, payload: dict):
        if not self.ws_manager:
            return
        import asyncio
        async def _send():
            try:
                await self.ws_manager.send({"type": event_type, **payload})
            except Exception:
                logger.exception("WebSocket emit failed")
        asyncio.create_task(_send())

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    def _init_database(self):
        logger.info("Initializing database...")
        init_db()                        # create_all + seed defaults
        self.SessionLocal = SessionLocal # factory — repos call this themselves
        self.engine = engine             # exposed for lifespan shutdown

    def get_db(self):
        """
        Return a fresh session. Caller is responsible for commit/close.
        Use this in background tasks and one-off operations.

        For FastAPI routes use the get_session dependency from session.py instead.
        """
        return self.SessionLocal()

    # ─────────────────────────────
    # REPOSITORIES
    # ─────────────────────────────
    def _init_repositories(self):
        logger.info("Initializing repositories...")

        # Repos receive the session factory, not a session.
        # Each repo method opens and closes its own session.
        # This is safe for background tasks and the request lifecycle.
        sf = self.SessionLocal

        self.stories_repo   = StoriesRepository(sf)
        self.users_repo     = UsersRepository(sf)
        self.files_repo     = FilesRepository(sf)
        self.chapters_repo  = ChaptersRepository(sf)
        self.progress_repo  = ProgressRepository(sf)
        self.sync_repo      = SyncRepository(self.chapters_repo)
        self.settings_repo  = SettingsRepository(sf)

    # ─────────────────────────────
    # SERVICES
    # ─────────────────────────────
    def _init_services(self):
        logger.info("Initializing services...")

        self.stories  = StoryService(self.stories_repo)
        self.users    = UserService(self.users_repo)
        self.auth     = AuthService(self.users_repo)
        self.files    = FileService(self.files_repo)
        self.chapters = ChaptersService(self.chapters_repo)
        self.progress = ProgressService(self.progress_repo)
        self.settings = SettingsService(self.settings_repo, settings_schema=SETTINGS)

    # ─────────────────────────────
    # FANFICFARE CONFIG
    # ─────────────────────────────
    def _init_fanficfare_config(self):
        logger.info("Initializing FanFicFare config...")
        self.fanficfare_config = FanFicFareConfigService(self.settings)
        self.fanficfare_config.write_config(force=True)
        self.settings_repo.on_change = self._on_settings_change

    def _on_settings_change(self, key: str):
        if key.startswith("fanficfare."):
            self.fanficfare_config.write_config(force=True)

    # ─────────────────────────────
    # UTILS
    # ─────────────────────────────
    def _init_utils(self):
        self.file_utils = FileUtils()

    # ─────────────────────────────
    # ENGINE
    # ─────────────────────────────
    def _init_engine(self):
        self.fanficfare_engine = FanFicFareEngine(
            self.settings_repo, self.fanficfare_config
        )
        self.engine_selector = EngineSelector(fanficfare_engine=self.fanficfare_engine)

    # ─────────────────────────────
    # PARSER REGISTRY
    # ─────────────────────────────
    def _init_parser_registry(self):
        self.parser_registry = ParserRegistry()
        self.parser_registry.register("fanficfare", FanFicFareParser())
        self.parser_registry.register("epub", EpubParser())
        self.parser_registry.register("html", HtmlParser())

    # ─────────────────────────────
    # PARSER
    # ─────────────────────────────
    def _init_parser(self):
        self.story_parser = StoryParser(self.parser_registry)

    # ─────────────────────────────
    # PIPELINE
    # ─────────────────────────────
    def _init_pipeline(self):
        self.story_pipeline = StoryPipeline(
            stories_repo=self.stories_repo,
            chapters_repo=self.chapters_repo,
            file_utils=self.file_utils,
        )

    # ─────────────────────────────
    # ORCHESTRATION
    # ─────────────────────────────
    def _init_orchestration(self):
        self.story_download = StoryDownloadService(
            selector=self.engine_selector,
            parser=self.story_parser,
            pipeline=self.story_pipeline,
        )

    # ─────────────────────────────
    # VALIDATION
    # ─────────────────────────────
    def _validate(self):
        required = [
            "engine",
            "SessionLocal",
            "stories_repo",
            "users_repo",
            "story_download",
            "parser_registry",
            "story_parser",
        ]
        for r in required:
            if not getattr(self, r, None):
                raise RuntimeError(f"Missing AppContext attr: {r}")
