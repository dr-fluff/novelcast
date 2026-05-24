# novelcast/api/routes/sync.py

from fastapi import APIRouter, BackgroundTasks, Depends

from novelcast.api.deps import get_library_sync
from novelcast.services import LibrarySyncService

router = APIRouter(tags=["sync"])


@router.post("/sync/all")
async def sync_all(
    background_tasks: BackgroundTasks,
    library_sync: LibrarySyncService = Depends(get_library_sync),
):
    background_tasks.add_task(library_sync.run_once)
    return {"status": "started"}
