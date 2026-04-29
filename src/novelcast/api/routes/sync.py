# novelcast/api/routes/sync.py

from fastapi import APIRouter, Request, BackgroundTasks
import anyio
import logging

log = logging.getLogger(__name__)

router = APIRouter()


def run_sync(ctx):
    stories = ctx.stories.get_all_stories()

    updates = 0

    for story in stories:
        try:
            result = ctx.story_download.sync_story(story)

            if result.get("new_chapters", 0) > 0:
                updates += 1

        except Exception:
            pass

    if updates > 0:
        ctx.notifier.broadcast({
            "type": "sync_update",
            "updates": updates
        })


@router.post("/sync/all")
async def sync_all(request: Request, background_tasks: BackgroundTasks):
    ctx = request.app.state.ctx

    background_tasks.add_task(run_sync, ctx)

    return {
        "status": "started"
    }