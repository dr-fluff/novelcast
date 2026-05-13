# novelcast/api/routes/download.py

from fastapi import APIRouter, Request
from pydantic import BaseModel
import anyio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class AddStoryRequest(BaseModel):
    url: str

@router.post("/download/story")
async def add_story(request: Request, body: AddStoryRequest):
    try:
        ctx = request.app.state.ctx

        result = await anyio.to_thread.run_sync(
            ctx.story_download.add_story,
            body.url
        )

    except Exception as e:
        logger.error("Error in add_story endpoint", exc_info=e)
        return {"status": "error", "message": str(e)}

    return {"status": "ok", "result": result}

