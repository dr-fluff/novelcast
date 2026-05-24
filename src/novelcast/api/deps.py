# novelcast/api/deps.py
#
# Single place that extracts services from app state.
# Routes import from here — they never touch request.app.state directly.

from fastapi import Request

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
)


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def get_users(request: Request) -> UserService:
    return request.app.state.users


def get_stories(request: Request) -> StoryService:
    return request.app.state.ctx.stories


def get_chapters(request: Request) -> ChaptersService:
    return request.app.state.ctx.chapters


def get_files(request: Request) -> FileService:
    return request.app.state.files


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


def get_templates(request: Request):
    return request.app.state.templates


def get_current_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)
