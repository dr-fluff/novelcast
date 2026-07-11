# novelcast/api/routes/sync.py

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from novelcast.api.deps import get_library_sync_service, get_stories_service
from novelcast.api.ws.notifications import manager
from novelcast.services import LibrarySyncService, StoryService

router = APIRouter(tags=["sync"])


class StorySelection(BaseModel):
    story_ids: list[int]


async def _tracked(job_id: str, label: str, fn, *args):
    async with manager.job(job_id, label) as job:
        await job.update(f"{label}…")
        await asyncio.get_event_loop().run_in_executor(None, lambda: fn(*args))


@router.post("/all")
async def sync_all(
    library_sync: LibrarySyncService = Depends(get_library_sync_service),
):
    job_id = f"sync-all-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(_tracked(job_id, "Checking all stories for updates", library_sync.check_updates))
    return {"status": "started", "job_id": job_id}


@router.post("/story/{story_id}")
async def sync_story(
    story_id: int,
    library_sync: LibrarySyncService = Depends(get_library_sync_service),
    stories: StoryService = Depends(get_stories_service),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    job_id = f"sync-{story_id}-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(
        _tracked(
            job_id,
            f"Checking '{story['title']}' for updates",
            library_sync.check_updates,
            [story_id],
        )
    )
    return {"status": "started", "job_id": job_id}


@router.post("/update/all")
async def update_all(
    library_sync: LibrarySyncService = Depends(get_library_sync_service),
):
    job_id = f"update-all-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(_tracked(job_id, "Updating all stories", library_sync.update_all))
    return {"status": "started", "job_id": job_id}


@router.post("/update/selected")
async def update_selected(
    selection: StorySelection,
    library_sync: LibrarySyncService = Depends(get_library_sync_service),
):
    job_id = f"update-selected-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(
        _tracked(
            job_id,
            f"Updating {len(selection.story_ids)} stories",
            library_sync.update_all,
            selection.story_ids,
        )
    )
    return {"status": "started", "job_id": job_id}


@router.post("/update/story/{story_id}")
async def update_story(
    story_id: int,
    library_sync: LibrarySyncService = Depends(get_library_sync_service),
    stories: StoryService = Depends(get_stories_service),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    job_id = f"update-{story_id}-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(_tracked(job_id, f"Updating '{story['title']}'", library_sync.update_all, [story_id]))
    return {"status": "started", "job_id": job_id}
