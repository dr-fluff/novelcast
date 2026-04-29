# novelcast/api/routes/download.py

from fastapi import APIRouter, Request
from pydantic import BaseModel
import anyio

router = APIRouter()

class AddStoryRequest(BaseModel):
    url: str

@router.post("/download/story")
async def add_story(request: Request, body: AddStoryRequest):
    ctx = request.app.state.ctx

    result = await anyio.to_thread.run_sync(
        ctx.story_download.add_story,
        body.url
    )

    return {"status": "ok", "result": result}

