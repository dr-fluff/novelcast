import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)


async def auto_sync_worker(ctx):
    logger.info("Auto-sync worker started")

    try:
        if ctx.library_sync.update_on_startup_enabled():
            await _run_auto_check(ctx)

        while True:
            if not ctx.library_sync.auto_sync_enabled():
                await asyncio.sleep(60)
                continue

            delay = ctx.library_sync.next_check_delay_seconds()
            await asyncio.sleep(delay)

            await _run_auto_check(ctx)

    except asyncio.CancelledError:
        logger.info("Auto-sync worker stopped")
        raise

    except Exception:
        logger.exception("Auto-sync worker crashed")


async def _run_auto_check(ctx):
    if not ctx.library_sync.auto_sync_enabled():
        return

    job_id = f"auto-sync-{uuid.uuid4().hex[:6]}"

        
    try:
        sync_svc = ctx.library_sync
        stories_svc = ctx.stories
        logger.info("Auto-sync check starting", extra={"job_id": job_id})

        auto_stories = [
            s["id"]
            for s in stories_svc.get_all_stories()
            if s.get("auto_update")
        ]

        if not auto_stories:
            await asyncio.to_thread(sync_svc.check_updates)
            return

        result = await asyncio.to_thread(sync_svc.check_updates, auto_stories)

        if result.get("pending_chapters", 0) > 0:
            await asyncio.to_thread(sync_svc.update_all, auto_stories)

    except Exception:
        logger.exception("Auto-sync check failed", extra={"job_id": job_id})