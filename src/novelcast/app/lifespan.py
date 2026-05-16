# novelcast/app/lifespan.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from novelcast.core.context import AppContext
from novelcast.api.ws.notifications import manager as ws_manager

from novelcast.db.repositories.password_reset_repository import PasswordResetRepository
from novelcast.services.password_reset_service import PasswordResetService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = None

    try:
        logger.info("Application starting...")

        # ─────────────────────────────
        # CONTEXT
        # ─────────────────────────────
        ctx = AppContext(app.state.config)

        # inject websocket system
        asyncio.create_task(event_worker(ctx))
        ctx.ws_manager = ws_manager

        # If orchestrator needs websocket (NOT service)
        ctx.story_orchestrator.notifier = ws_manager

        # expose to app
        app.state.ctx = ctx
        app.state.db = ctx.SessionLocal
        app.state.users = ctx.users
        app.state.auth = ctx.auth
        app.state.settings = ctx.settings

        # ─────────────────────────────
        # PASSWORD RESET SERVICE
        # ─────────────────────────────
        password_reset_repo = PasswordResetRepository(ctx.SessionLocal)

        ctx.password_reset = PasswordResetService(
            repo=password_reset_repo,
            users_repo=ctx.users_repo,
            auth_service=ctx.auth,
        )

        app.state.password_reset = ctx.password_reset
        app.state.ws_manager = ws_manager

        logger.info("Application startup complete")

        yield

    except Exception:
        logger.exception("Application failed to start")
        raise

    finally:
        logger.info("Application shutting down...")
        try:
            if ctx and ctx.engine:
                ctx.engine.dispose()
                logger.info("Database engine disposed")
        except Exception:
            logger.exception("Shutdown cleanup failed")
            


async def event_worker(ctx):
    while True:
        event_type, payload = await asyncio.to_thread(ctx.event_queue.get)
        try:
            await ctx.ws_manager.send({"type": event_type, **payload})
        except Exception:
            logger.exception("WebSocket send failed")