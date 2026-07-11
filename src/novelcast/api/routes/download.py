# novelcast/api/routes/download.py
import logging

import anyio
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from novelcast.api.deps import get_download
from novelcast.services.story_download_service import StoryDownloadService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["download"])


class AddStoryRequest(BaseModel):
    url: str


@router.post("/download/story")
async def add_story(
    body: AddStoryRequest,
    download: StoryDownloadService = Depends(get_download),
):
    """
    Entry point for starting a story download.

    Flow:
    API → StoryDownloadService → Orchestrator → Engine
    """
    try:
        result = await anyio.to_thread.run_sync(
            download.add_story,
            body.url,
        )

    except Exception as e:
        logger.error("Error in add_story endpoint", exc_info=e)
        return {
            "status": "error",
            "message": str(e),
        }

    return {
        "status": "ok",
        "result": result,
    }
