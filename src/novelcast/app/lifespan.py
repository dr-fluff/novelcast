# novelcast/app/lifespan.py

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from novelcast.api.ws.notifications import manager as ws_manager
from novelcast.core.context import AppContext
from novelcast.core.defaults import DEFAULT_CHAPTER_PATTERNS
from novelcast.core.logging import log_buffer
from novelcast.db.repositories import PasswordResetRepository
from novelcast.services import (
    LoggingService,
    NotifierService,
    PasswordResetService,
    TelegramService,
)
from novelcast.services.workers import auto_sync_worker

logger = logging.getLogger(__name__)


async def event_dispatcher(queue: asyncio.Queue, ws_manager):
    while True:
        event_type, payload = await queue.get()
        try:
            await ws_manager.broadcast(event_type, payload)
        except Exception:
            logger.exception("Failed to broadcast websocket event")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = None
    sync_task = None
    dispatcher_task = None
    telegram = None

    try:
        logger.info("Application starting...")

        # ─────────────────────────────
        # CORE CONTEXT
        # ─────────────────────────────
        ctx = AppContext(app.state.config)
        app.state.ctx = ctx

        logging_service = LoggingService(ctx.settings)
        logging_service.apply()
        ctx.logging_service = logging_service
        ctx.log_buffer = log_buffer

        try:
            added = ctx.chapter_pattern_repo.seed_defaults(DEFAULT_CHAPTER_PATTERNS)
            logger.info("Added %d missing chapter patterns" if added else "Chapter patterns already exist")
        except Exception:
            logger.exception("Failed to seed chapter patterns")

        # ─────────────────────────────
        # WEBSOCKETS + EVENT QUEUE
        # ─────────────────────────────
        ctx.ws_manager = ws_manager

        event_queue = asyncio.Queue()
        app.state.event_queue = event_queue

        app.state.loop = asyncio.get_running_loop()
        ctx.loop = app.state.loop
        ctx.notifier = NotifierService(ws_manager=ws_manager, loop=ctx.loop)

        # ─────────────────────────────
        # TELEGRAM
        # ─────────────────────────────
        telegram = TelegramService(
            ctx.settings,
            ctx.stories,
            ctx.story_download,
        )

        telegram.start()

        ctx.story_download.telegram = telegram
        ctx.stories.telegram = telegram
        app.state.telegram = telegram

        # ─────────────────────────────
        # APP STATE EXPOSURE
        # ─────────────────────────────
        app.state.db = ctx.SessionLocal
        app.state.users = ctx.users
        app.state.auth = ctx.auth
        app.state.settings = ctx.settings

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

        # ✅ STEP 4: dispatcher task (THIS WAS MISSING)
        dispatcher_task = asyncio.create_task(event_dispatcher(event_queue, ws_manager))
        app.state.dispatcher_task = dispatcher_task

        logger.info("Application startup complete")

        yield

    except Exception:
        logger.exception("Application failed to start")
        raise

    finally:
        logger.info("Application shutting down...")

        # ─────────────────────────────
        # STOP TELEGRAM
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

        # STOP DISPATCHER
        if dispatcher_task:
            dispatcher_task.cancel()
            try:
                await dispatcher_task
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
