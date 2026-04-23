import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from novelcast.core.context import AppContext
from novelcast.core.config import AppConfig
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = None
    ctx = None

    try:
        # -------------------------
        # CONFIG + CORE CONTEXT
        # -------------------------
        config = AppConfig()
        ctx = AppContext()

        logger.info(
            "Initializing application context",
            extra={"extra_data": {"env": config.env}},
        )

        # -------------------------
        # SERVICES
        # -------------------------
        user_service = UserService(ctx.qm)
        auth_service = AuthService(ctx.qm)

        # -------------------------
        # APP STATE REGISTRATION
        # -------------------------
        app.state.ctx = ctx
        app.state.db = ctx.db
        app.state.qm = ctx.qm

        app.state.users = user_service
        app.state.auth = auth_service
        app.state.config = config

        # -------------------------
        # CONFIG LOGGING (NO PRINT)
        # -------------------------
        logger.info(
            "Application configuration loaded",
            extra={
                "extra_data": {
                    k: v for k, v in config.model_dump().items()
                }
            },
        )

        logger.info("Application startup complete")

        yield

    except Exception:
        logger.exception("Fatal error during application startup")
        raise

    finally:
        try:
            if ctx and ctx.db:
                ctx.db.close()
                logger.info("Database connection closed cleanly")

        except Exception:
            logger.exception("Error while closing database connection")