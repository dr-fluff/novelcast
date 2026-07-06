# novelcast/api/deps.py
from fastapi import Request

from novelcast.engine import PatreonEngine

from novelcast.services import (
    AuthService,
    UserService,
    ChaptersService,
    FileService,
    ProgressService,
    SettingsService,
    StoryDownloadService,
    StoryService,
    LibrarySyncService,
    NotifierService,
    PasswordResetService,
    HealthCheckService,
    ChapterFilterService,
    TelegramService,
    LoggingService,
)

# ─────────────────────────────
# CORE SERVICES (direct app.state)
# ─────────────────────────────

def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def get_users(request: Request) -> UserService:
    return request.app.state.users


def get_files(request: Request) -> FileService:
    return request.app.state.files


def get_session_factory(request: Request):
    return request.app.state.db


def get_current_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


def get_templates(request: Request):
    return request.app.state.templates


# ─────────────────────────────
# CONTEXT SERVICES (ctx-based)
# ─────────────────────────────

def get_stories(request: Request) -> StoryService:
    return request.app.state.ctx.stories


def get_chapters(request: Request) -> ChaptersService:
    return request.app.state.ctx.chapters


def get_progress(request: Request) -> ProgressService:
    return request.app.state.ctx.progress


def get_settings(request: Request) -> SettingsService:
    return request.app.state.ctx.settings


def get_download(request: Request) -> StoryDownloadService:
    return request.app.state.ctx.story_download


def get_library_sync(request: Request) -> LibrarySyncService:
    return request.app.state.ctx.library_sync


def get_notifier(request: Request) -> NotifierService:
    return request.app.state.ctx.notifier


def get_password_reset(request: Request) -> PasswordResetService:
    return request.app.state.ctx.password_reset


def get_chapter_filter(request: Request) -> ChapterFilterService:
    return request.app.state.ctx.chapter_filter


def get_health_check(request: Request) -> HealthCheckService:
    return request.app.state.ctx.health_check


def get_telegram(request: Request) -> TelegramService:
    return request.app.state.ctx.telegram

def get_library_sync_service(request: Request) -> LibrarySyncService:
    return request.app.state.ctx.library_sync

def get_stories_service(request: Request) -> StoryService:
    return request.app.state.ctx.stories

def get_logs(request: Request) -> LoggingService:
    return request.app.state.ctx.logs

def get_patreon_engine(request: Request) -> PatreonEngine:
    return request.app.state.ctx.patreon_engine

