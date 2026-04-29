import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from novelcast.core.context import AppContext
from novelcast.core.config import AppConfig

from novelcast.api.ws.notifications import manager as ws_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = None

    try:
        config = AppConfig()
        ctx = AppContext()

        logger.debug(
            "Application starting",
            extra={
                "extra_data": {
                    "env": config.env,
                }
            },
        )

        app.state.ws_manager = ws_manager
        ctx.story_download.ws_manager = ws_manager

        app.state.ctx = ctx
        app.state.db = ctx.db
        app.state.qm = ctx.qm
        app.state.users = ctx.users
        app.state.auth = ctx.auth
        app.state.settings = ctx.settings
        app.state.config = config

        logger.info("Application startup complete")

        yield

    except Exception:
        logger.exception("Application failed to start")
        raise

    finally:
        try:
            if ctx and ctx.db:
                ctx.db.close()
                logger.info("Database connection closed")

        except Exception:
            logger.exception("Error during shutdown cleanup")