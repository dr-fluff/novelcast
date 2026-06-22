# novelcast/api/routes/add_story.py

import logging
import uuid
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from novelcast.api.deps import get_download_service, get_stories_service
from novelcast.api.ws.notifications import manager
from novelcast.services import StoryService, StoryDownloadService

router = APIRouter(prefix="/stories", tags=["stories"])
logger = logging.getLogger(__name__)


class Chapter(BaseModel):
    number: int
    title: Optional[str] = None
    selected: bool


class AddStoryRequest(BaseModel):
    url: str
    title: str | None = None
    author: str | None = None
    subtitle: str | None = None
    description: str | None = None
    publish_year: int | None = None
    language: str | None = None
    series: list[str] | None = None
    genres: list[str] | None = None
    tags: list[str] | None = None
    auto_update: bool = False
    selected_chapters: list[int] | None = None


class MetadataPreview(BaseModel):
    url: str
    title: str | None
    author: str | None
    subtitle: str | None
    description: str | None
    publish_year: int | None
    language: str | None
    series: list[str] | None
    genres: list[str] | None
    tags: list[str] | None
    chapter_count: int | None
    chapters: list[Chapter] | None
    story_site_id: str | None


@router.post("/preview")
async def preview_story_metadata(
    request: AddStoryRequest,
    download: StoryDownloadService = Depends(get_download_service),
) -> MetadataPreview:
    try:
        result = download.orchestrator.check_updates(request.url)
        chapters = result.get("chapters") or []
        raw = result.get("raw") or {}
        if not isinstance(chapters, list):
            chapters = []
        metadata = download._extract_metadata(raw)
        return MetadataPreview(
            url=request.url,
            title=metadata.get("title"),
            author=metadata.get("author"),
            subtitle=metadata.get("subtitle"),
            description=metadata.get("description"),
            publish_year=metadata.get("publish_year"),
            language=metadata.get("language"),
            series=metadata.get("series"),
            genres=metadata.get("genres"),
            tags=metadata.get("tags"),
            chapter_count=len(chapters),
            chapters=chapters,
            story_site_id=raw.get("storyId") or raw.get("story_site_id"),
        )
    except Exception as e:
        logger.exception("Failed to preview story metadata")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/add")
async def add_story_with_metadata(
    request: Request,
    body: AddStoryRequest,
    download: StoryDownloadService = Depends(get_download_service),
    stories: StoryService = Depends(get_stories_service),
):
    title_hint = body.title or body.url
    job_id = f"download-{uuid.uuid4().hex[:6]}"
    asyncio.create_task(_download_story(job_id, title_hint, body, download, stories))
    return {"status": "started", "job_id": job_id}


async def _download_story(
    job_id: str,
    title_hint: str,
    body: AddStoryRequest,
    download: StoryDownloadService,
    stories: StoryService,
):
    async with manager.job(job_id, f"Adding '{title_hint}'") as job:
        await job.update("Downloading chapters…")
        story_id = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download.add_story(
                body.url,
                selected_chapters=body.selected_chapters,
            ),
        )
        await job.update("Saving metadata…", progress=90)
        stories.update_story_metadata(
            story_id=story_id,
            title=body.title,
            author=body.author,
            subtitle=body.subtitle,
            description=body.description,
            publish_year=body.publish_year,
            language=body.language,
            series=body.series,
            genres=body.genres,
            tags=body.tags,
            auto_update=body.auto_update,
        )