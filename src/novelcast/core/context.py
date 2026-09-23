# novelcast/core/context.py
import logging
import threading
from queue import Queue
from pathlib import Path

from novelcast.core import setting_keys
from novelcast.core.defaults import (
    LIBRARY_DATABASE_PATH,
    REQUIRED_USER_SETTINGS,
    SECTION_LIBRARY,
    SECTION_RSS,
    SECTION_TELEGRAM,
    SETTINGS,
    USER_SETTINGS_SCHEMA,
)
from novelcast.db.engine import db_path_from_url, engine
from novelcast.db.init_db import init_db
from novelcast.db.repositories import (
    AuthorRepository,
    ChaptersRepository,
    FilesRepository,
    ProgressRepository,
    RssEntryRepository,
    SettingsRepository,
    StatsRepository,
    StoriesRepository,
    SyncRepository,
    UsersRepository,
)
from novelcast.db.repositories.chapter_pattern_repository import (
    ChapterPatternRepository,
)
from novelcast.db.session import SessionLocal
from novelcast.engine import (
    EngineSelector,
    FanFicFareEngine,
    PatreonEngine,
    StoryDownloadOrchestrator,
)
from novelcast.parser import (
    EpubParser,
    FanFicFareParser,
    HtmlParser,
    ParserRegistry,
    PatreonParser,
    StoryParser,
)
from novelcast.pipeline.story_pipeline import StoryPipeline
from novelcast.services import (
    AuthService,
    ChaptersService,
    FanFicFareConfigService,
    FileService,
    HealthCheckService,
    LibrarySyncService,
    ProgressService,
    RssService,
    SettingsService,
    StoryDownloadService,
    StoryService,
    TelegramService,
    UserService,
)
from novelcast.services.chapter_filter_service import ChapterFilterService
from novelcast.services.database_relocation_service import (
    DatabaseRelocationError,
    DatabaseRelocationService,
)
from novelcast.services.stats_service import StatsService
from novelcast.utils.files import FileUtils

logger = logging.getLogger(__name__)

_RESTART_DEBOUNCE_SECONDS = 1.0
_DATABASE_PATH_KEY = f"{SECTION_LIBRARY}.{LIBRARY_DATABASE_PATH}"
_DATABASE_RELOCATION_TIMER_KEY = "database_path"


class AppContext:
    def __init__(self, app_config):
        logger.info("Starting AppContext initialization")

        self.app_config = app_config
        self.event_queue = Queue()
        self.ws_manager = None

        self.loop = None

        self.runtime_services = {}
        self._restart_timers = {}
        self._restart_lock = threading.Lock()

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
        self._init_telegram()
        self._init_rss()
        self._validate()

        logger.info("AppContext ready")

    # ─────────────────────────────
    # EVENTS
    # ─────────────────────────────
    def emit(self, event_type: str, payload: dict):
        if not self.notifier:
            return
        self.notifier.broadcast(event_type, payload)

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    def _init_database(self):
        resolved_path = Path(
            db_path_from_url(self.app_config.database_url)
        ).resolve()

        logger.info(
            "Database path resolved",
            extra={
                "extra_data": {
                    "database_url": self.app_config.database_url,
                    "resolved_path": str(resolved_path),
                    "file_exists": resolved_path.exists(),
                    "file_size": (
                        resolved_path.stat().st_size
                        if resolved_path.exists()
                        else None
                    ),
                }
            },
        )

        logger.info("Initializing database...")
        init_db()

        self.SessionLocal = SessionLocal
        self.engine = engine
        self.database_relocation = DatabaseRelocationService(
            engine=self.engine,
            session_factory=self.SessionLocal,
            current_db_path=db_path_from_url(self.app_config.database_url),
            on_engine_replaced=self._on_engine_replaced,
        )

    def _on_engine_replaced(self, new_engine):
        self.engine = new_engine

    def get_db(self):
        return self.SessionLocal()

    # ─────────────────────────────
    # REPOSITORIES
    # ─────────────────────────────
    def _init_repositories(self):
        logger.info("Initializing repositories...")

        sf = self.SessionLocal

        self.stories_repo = StoriesRepository(sf)
        self.authors_repo = AuthorRepository(sf)
        self.users_repo = UsersRepository(sf)
        self.files_repo = FilesRepository(sf)
        self.chapters_repo = ChaptersRepository(sf)
        self.progress_repo = ProgressRepository(sf)
        self.stats_repo = StatsRepository(sf)
        self.sync_repo = SyncRepository(self.chapters_repo)
        self.settings_repo = SettingsRepository(sf, user_settings_schema=USER_SETTINGS_SCHEMA)
        self.chapter_pattern_repo = ChapterPatternRepository(sf)
        self.rss_entry_repo = RssEntryRepository(sf)

    # ─────────────────────────────
    # SERVICES (business logic)
    # ─────────────────────────────
    def _init_services(self):
        logger.info("Initializing services...")

        self.stories = StoryService(self.stories_repo, author_repo=self.authors_repo)
        restored_covers = self.stories.restore_local_cover_paths()
        if restored_covers:
            logger.info("Restored cover paths for %d stories", restored_covers)
        self.users = UserService(self.users_repo)
        self.auth = AuthService(self.users_repo)
        self.files = FileService(self.files_repo)
        self.chapters = ChaptersService(self.chapters_repo)
        self.progress = ProgressService(self.progress_repo)
        self.stats = StatsService(self.stats_repo)

        self.settings = SettingsService(
            self.settings_repo,
            settings_schema=SETTINGS,
            user_settings_schema=USER_SETTINGS_SCHEMA,
            required_user_settings=REQUIRED_USER_SETTINGS,
            secret_key=self.app_config.secret_key,
        )
        self.settings.migrate_server_secrets()

        self.chapter_filter = ChapterFilterService(self.chapter_pattern_repo)

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
        }

        for cfg in self.engines_config.values():
            cfg["writer"].write_config(force=True)

        self.settings_repo.on_change = self._on_settings_change

    def _on_settings_change(self, key: str):
        if key == _DATABASE_PATH_KEY:
            self._handle_database_relocation(key)
            return

        for cfg in self.engines_config.values():
            if key.startswith(cfg["prefix"]):
                cfg["writer"].write_config(force=False)
                return

        for prefix, service in self.runtime_services.items():
            if key.startswith(f"{prefix}."):
                self._schedule_restart(prefix, service, key)
                return

    def _handle_database_relocation(self, key: str):
        new_path = self.settings_repo.get_server_setting(key)
        if not new_path:
            logger.warning("Database relocation triggered but no path found for %s", key)
            return

        try:
            self.database_relocation.relocate(new_path)
        except DatabaseRelocationError:
            logger.exception("Database relocation to %r failed", new_path)

    def _schedule_restart(self, prefix: str, service, key: str):

        def _do_restart():
            logger.info("%s settings changed (%s); restarting", prefix, key)

            if getattr(service, "requires_event_loop", False):
                if not self.loop:
                    logger.warning(
                        "%s requires an event loop but none is set yet; skipping restart",
                        prefix,
                    )
                else:
                    self.loop.call_soon_threadsafe(service.stop)
                    self.loop.call_soon_threadsafe(service.start)
            else:
                service.stop()
                service.start()

            with self._restart_lock:
                self._restart_timers.pop(prefix, None)

        with self._restart_lock:
            existing = self._restart_timers.get(prefix)
            if existing:
                existing.cancel()

            timer = threading.Timer(_RESTART_DEBOUNCE_SECONDS, _do_restart)
            timer.daemon = True
            self._restart_timers[prefix] = timer
            timer.start()

    def _schedule_database_relocation(self, key: str):
        def _do_relocate():
            new_path = self.settings_repo.get_server_setting(key)
            if not new_path:
                logger.warning("Database relocation triggered but no path found for %s", key)
                return

            if self.app_config.reload:
                logger.error(
                    "Refusing to relocate database while auto-reload is enabled (RELOAD=true): "
                    "the app cannot safely continue running against the old engine after the "
                    "file is moved, and reload mode won't restart the process automatically. "
                    "Set RELOAD=false (or run via `docker compose up`) before changing this setting."
                )
                return

            try:
                self.database_relocation.prepare(new_path)
            except DatabaseRelocationError:
                logger.exception("Database relocation to %r failed", new_path)
                return

            logger.info("Database relocated to %r; restarting", new_path)
            self.database_relocation.restart()

            with self._restart_lock:
                self._restart_timers.pop(_DATABASE_RELOCATION_TIMER_KEY, None)

        with self._restart_lock:
            existing = self._restart_timers.get(_DATABASE_RELOCATION_TIMER_KEY)
            if existing:
                existing.cancel()

            timer = threading.Timer(_RESTART_DEBOUNCE_SECONDS, _do_relocate)
            timer.daemon = True
            self._restart_timers[_DATABASE_RELOCATION_TIMER_KEY] = timer
            timer.start()

    # ─────────────────────────────
    # TELEGRAM
    # ─────────────────────────────
    def _init_telegram(self):
        logger.info("Initializing Telegram service...")

        self.telegram = TelegramService(
            self.settings,
            self.stories,
            self.story_download,
            self.library_sync,
        )

        self.story_download.telegram = self.telegram
        self.stories.telegram = self.telegram

        self.runtime_services[SECTION_TELEGRAM] = self.telegram

    # ─────────────────────────────
    # UTILS
    # ─────────────────────────────
    def _init_utils(self):
        self.file_utils = FileUtils()

    def _init_rss(self):
        logger.info("Initializing RSS service...")

        self.rss = RssService(
            settings=self.settings,
            story_service=self.stories,
            download_service=self.story_download,
            rss_repo=self.rss_entry_repo,
            chapter_filter=self.chapter_filter,
        )

        self.rss.start()

        self.runtime_services[SECTION_RSS] = self.rss

    # ─────────────────────────────
    # ENGINE (fetch only)
    # ─────────────────────────────
    def _init_engine(self):
        logger.info("Initializing engines...")

        data_path = self.settings.get(setting_keys.LIBRARY_SETTINGS.DATA_PATH).value

        self.fanficfare_engine = FanFicFareEngine(
            self.settings_repo,
            self.engines_config["fanficfare"]["writer"],
            download_dir=data_path,
        )

        self.patreon_engine = PatreonEngine(
            self.settings_repo,
            self.settings,
        )

        self.engine_selector = EngineSelector(
            [
                self.fanficfare_engine,
                self.patreon_engine,
            ]
        )

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
            settings_service=self.settings,
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