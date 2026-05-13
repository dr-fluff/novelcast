# novelcast/app/lifespan.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

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
        ctx.ws_manager = ws_manager
        ctx.story_download.ws_manager = ws_manager

        # expose to app
        app.state.ctx      = ctx
        app.state.db       = ctx.SessionLocal   # ← now a factory, not a connection
        app.state.users    = ctx.users
        app.state.auth     = ctx.auth
        app.state.settings = ctx.settings

        # ─────────────────────────────
        # PASSWORD RESET SERVICE
        # ─────────────────────────────
        password_reset_repo = PasswordResetRepository(ctx.SessionLocal)

        ctx.password_reset = PasswordResetService(
            repo=password_reset_repo,
            users_repo=ctx.users_repo,       # ← was ctx.users (a service), should be the repo
            auth_service=ctx.auth,
        )
        app.state.password_reset = ctx.password_reset

        # ─────────────────────────────
        # WEBSOCKETS
        # ─────────────────────────────
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
                ctx.engine.dispose()        # cleanly close the connection pool
                logger.info("Database engine disposed")
        except Exception:
            logger.exception("Shutdown cleanup failed")
