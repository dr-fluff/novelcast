# novelcast/api/routes/sync.py

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from novelcast.api.deps import get_library_sync, get_stories
from novelcast.services import LibrarySyncService, StoryService

router = APIRouter(tags=["sync"])


class StorySelection(BaseModel):
    story_ids: list[int]


@router.post("/sync/all")
async def sync_all(
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    background_tasks.add_task(library_sync.check_updates)
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

    background_tasks.add_task(library_sync.check_updates, [story_id])
    return {"status": "started", "story_id": story_id}


@router.post("/update/all")
async def update_all(
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    background_tasks.add_task(library_sync.update_all)
    return {"status": "started"}


@router.post("/update/selected")
async def update_selected(
    selection: StorySelection,
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    background_tasks.add_task(library_sync.update_all, selection.story_ids)
    return {"status": "started", "story_ids": selection.story_ids}


@router.post("/update/story/{story_id}")
async def update_story(
    story_id: int,
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    background_tasks.add_task(library_sync.update_all, [story_id])
    return {"status": "started", "story_id": story_id}
