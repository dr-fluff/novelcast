# novelcast/api/routes/add_story.py

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from novelcast.api.deps import get_stories, get_download
from novelcast.services import StoryService, StoryDownloadService

router = APIRouter(prefix="/stories", tags=["stories"])
logger = logging.getLogger(__name__)


from typing import Optional

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
    selected_chapters: list[int] | None = None  # ← NEW


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


# ── Preview metadata without downloading ───────────────────────────────

@router.post("/preview")
async def preview_story_metadata(
    request: AddStoryRequest,
    download: StoryDownloadService = Depends(get_download),
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

# ── Add story with pre-configured metadata ─────────────────────────────

@router.post("/add")
async def add_story_with_metadata(
    request: AddStoryRequest,
    background_tasks: BackgroundTasks,
    download: StoryDownloadService = Depends(get_download),
    stories: StoryService = Depends(get_stories),
):
    try:
        # Validate URL is not already being downloaded / already exists
        # (optional guard — add if you want to prevent duplicates)

        def run_download():
            try:
                story_id = download.add_story(
                    request.url,
                    selected_chapters=request.selected_chapters,
                )
                stories.update_story_metadata(
                    story_id=story_id,
                    title=request.title,
                    author=request.author,
                    subtitle=request.subtitle,
                    description=request.description,
                    publish_year=request.publish_year,
                    language=request.language,
                    series=request.series,
                    genres=request.genres,
                    tags=request.tags,
                    auto_update=request.auto_update,
                )
            except Exception as e:
                logger.exception("Background download failed for %s", request.url)

        background_tasks.add_task(run_download)

        return {
            "status": "started",
            "auto_update": request.auto_update,
            "selected_chapters": request.selected_chapters or "all",
        }

    except Exception as e:
        logger.exception("Failed to start story download")
        raise HTTPException(status_code=400, detail=f"Failed to start download: {str(e)}")