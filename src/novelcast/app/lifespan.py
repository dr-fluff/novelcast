# novelcast/app/lifespan.py

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from novelcast.core.context import AppContext
from novelcast.api.ws.notifications import manager as ws_manager
from novelcast.core.defaults import DEFAULT_CHAPTER_PATTERNS

from novelcast.db.repositories import (
    PasswordResetRepository,
    )

from novelcast.services import (
    PasswordResetService, 
    TelegramService, 
    NotifierService
    )

from novelcast.services.workers import auto_sync_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = None
    sync_task = None
    telegram = None

    try:
        logger.info("Application starting...")

        # ─────────────────────────────
        # CORE CONTEXT (NO TELEGRAM HERE)
        # ─────────────────────────────
        ctx = AppContext(app.state.config)
        app.state.ctx = ctx

        # seed defaults
        try:
            added = ctx.chapter_pattern_repo.seed_defaults(DEFAULT_CHAPTER_PATTERNS)
            logger.info(
                "Added %d missing chapter patterns" if added else "Chapter patterns already exist"
            )
        except Exception:
            logger.exception("Failed to seed chapter patterns")

        # websockets
        ctx.ws_manager = ws_manager
        ctx.story_orchestrator.notifier = ws_manager
        ctx.notifier = NotifierService(ws_manager=ws_manager)
        ctx.ws_manager = ws_manager

        # ─────────────────────────────
        # TELEGRAM (LIFESPAN OWNED)
        # ─────────────────────────────
        telegram = TelegramService(
            ctx.settings,
            ctx.stories,
            ctx.story_download,
        )

        telegram.start()
        
        ctx.story_download.telegram = telegram
        ctx.stories.telegram = telegram

        # expose only if needed (optional)
        app.state.telegram = telegram

        # ─────────────────────────────
        # APP STATE EXPOSURE
        # ─────────────────────────────
        app.state.db = ctx.SessionLocal
        app.state.users = ctx.users
        app.state.auth = ctx.auth
        app.state.settings = ctx.settings

        # password reset
        password_reset_repo = PasswordResetRepository(ctx.SessionLocal)
        ctx.password_reset = PasswordResetService(
            repo=password_reset_repo,
            users_repo=ctx.users_repo,
            auth_service=ctx.auth,
        )
        app.state.password_reset = ctx.password_reset

        # ─────────────────────────────
        # BACKGROUND WORKERS
        # ─────────────────────────────
        sync_task = asyncio.create_task(auto_sync_worker(ctx))

        logger.info("Application startup complete")

        yield

    except Exception:
        logger.exception("Application failed to start")
        raise

    finally:
        logger.info("Application shutting down...")

        # ─────────────────────────────
        # STOP TELEGRAM FIRST
        # ─────────────────────────────
        if telegram:
            try:
                telegram.stop()
            except Exception:
                logger.exception("Failed to stop Telegram service")

        # ─────────────────────────────
        # STOP WORKERS
        # ─────────────────────────────
        if sync_task:
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass

        # ─────────────────────────────
        # DB CLEANUP
        # ─────────────────────────────
        try:
            if ctx and ctx.engine:
                ctx.engine.dispose()
                logger.info("Database engine disposed")
        except Exception:
            logger.exception("Shutdown cleanup failed")