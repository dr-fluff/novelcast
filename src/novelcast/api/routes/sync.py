# novelcast/api/routes/sync.py

import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from novelcast.api.deps import get_download, get_notifier, get_stories
from novelcast.services import StoryDownloadService, NotifierService, StoryService

log = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])


def _run_sync(
    stories: StoryService,
    download: StoryDownloadService,
    notifier: NotifierService,
) -> None:
    updates = 0

    for story in stories.get_all_stories():
        try:
            result = download.sync_story(story)
            if result.get("new_chapters", 0) > 0:
                updates += 1
        except Exception:
            log.exception("Failed to sync story %s", story.get("id"))

    if updates > 0:
        notifier.broadcast({"type": "sync_update", "updates": updates})


@router.post("/sync/all")
async def sync_all(
    background_tasks: BackgroundTasks,
    stories: StoryService = Depends(get_stories),
    download: StoryDownloadService = Depends(get_download),
    notifier: NotifierService = Depends(get_notifier),
):
    background_tasks.add_task(_run_sync, stories, download, notifier)
    return {"status": "started"}