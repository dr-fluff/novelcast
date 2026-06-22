# novelcast/app/lifespan.py

import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from novelcast.core.context import AppContext
from novelcast.api.ws.notifications import manager as ws_manager

from novelcast.core.defaults import DEFAULT_CHAPTER_PATTERNS
from novelcast.db.repositories.password_reset_repository import PasswordResetRepository
from novelcast.services.password_reset_service import PasswordResetService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = None
    sync_task = None

    try:
        logger.info("Application starting...")

        ctx = AppContext(app.state.config)

        try:
            ctx.chapter_pattern_repo.seed_defaults(DEFAULT_CHAPTER_PATTERNS)
            logger.info("Chapter patterns seeded")
        except Exception:
            logger.exception("Failed to seed chapter patterns")

        ctx.ws_manager = ws_manager
        ctx.story_orchestrator.notifier = ws_manager

        app.state.ctx = ctx
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
        app.state.ws_manager = ws_manager

        sync_task = asyncio.create_task(auto_sync_worker(ctx))

        logger.info("Application startup complete")
        yield

    except Exception:
        logger.exception("Application failed to start")
        raise

    finally:
        logger.info("Application shutting down...")
        if sync_task:
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass
        try:
            if ctx and ctx.engine:
                ctx.engine.dispose()
                logger.info("Database engine disposed")
        except Exception:
            logger.exception("Shutdown cleanup failed")


async def auto_sync_worker(ctx):
    if ctx.library_sync.update_on_startup_enabled():
        await _run_auto_check(ctx)

    while True:
        if not ctx.library_sync.auto_sync_enabled():
            await asyncio.sleep(60)
            continue

        await asyncio.sleep(ctx.library_sync.next_check_delay_seconds())
        await _run_auto_check(ctx)


async def _run_auto_check(ctx):
    if not ctx.library_sync.auto_sync_enabled():
        return

    job_id = f"auto-sync-{uuid.uuid4().hex[:6]}"

    try:
        # Use a fresh session for this background operation
        with ctx.SessionLocal() as session:
            from novelcast.services import LibrarySyncService, StoryService
            stories_svc = StoryService(session)
            sync_svc = LibrarySyncService(session)

            auto_stories = [
                s["id"]
                for s in stories_svc.get_all_stories()
                if s.get("auto_update")
            ]

            async with ws_manager.job(job_id, "Auto-sync") as job:
                if not auto_stories:
                    await job.update("Checking all stories for updates…")
                    await asyncio.to_thread(sync_svc.check_updates)
                    return

                await job.update(f"Checking {len(auto_stories)} stories for updates…")
                result = await asyncio.to_thread(sync_svc.check_updates, auto_stories)

                if result.get("pending_chapters", 0) > 0:
                    await job.update(
                        f"Downloading {result['pending_chapters']} new chapters…",
                        progress=50,
                    )
                    await asyncio.to_thread(sync_svc.update_all, auto_stories)

    except Exception:
        logger.exception("Automatic update check failed")