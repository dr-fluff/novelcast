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

    await anyio.to_thread.run_sync(
        ctx.downloader.sync_story,
        body.url
    )

    return {
        "status": "ok",
        "url": body.url
    }