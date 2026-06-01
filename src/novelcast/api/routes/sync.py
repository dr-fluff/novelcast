# novelcast/api/routes/sync.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from novelcast.api.deps import get_library_sync, get_stories
from novelcast.services import LibrarySyncService, StoryService

router = APIRouter(tags=["sync"])


@router.post("/sync/all")
async def sync_all(
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    background_tasks.add_task(library_sync.run_once)
    return {"status": "started"}


@router.post("/sync/story/{story_id}")
async def sync_story(
    story_id: int,
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    background_tasks.add_task(library_sync.download.sync_story, story)
    return {"status": "started", "story_id": story_id}
