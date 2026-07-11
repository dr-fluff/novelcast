# novelcast/api/routes/add_story.py

import asyncio
import hashlib
import logging
import uuid
from typing import Optional
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from novelcast.api.deps import get_download, get_patreon_engine, get_stories_service
from novelcast.api.ws.notifications import manager
from novelcast.engine.engine_patreon import PatreonEngine
from novelcast.services import StoryDownloadService, StoryService

router = APIRouter(tags=["stories"])
logger = logging.getLogger(__name__)


class Chapter(BaseModel):
    number: int
    title: Optional[str] = None
    selected: bool
    locked: bool = False


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
    chapter_regex: str | None = None
    content_source: str | None = None  # "file" or "text" — Patreon only
    filename_pattern: str | None = None  # regex with (?P<number>) (?P<title>) — Patreon only


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


def _is_patreon_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"patreon.com", "www.patreon.com"}


def _extract_patreon_creator(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    vanity = (query.get("vanity") or [None])[0]
    if vanity:
        return vanity.strip()

    parts = [segment for segment in parsed.path.split("/") if segment]
    if parts and parts[0].lower() == "c" and len(parts) > 1:
        return parts[1]
    if parts:
        return parts[0]
    return "Patreon Creator"


def patreon_key(creator: str) -> str:
    return f"patreon:{creator}"


def normalize_patreon_creator(url: str) -> tuple[str, str]:
    parts = url.split("patreon.com/")[-1].split("/")
    if parts[0] == "c":
        return parts[1], "c"
    if parts[0] == "cw":
        return parts[1], "cw"
    raise ValueError("Not a Patreon creator URL")


def canonical_patreon_url(url: str) -> str:
    creator = _extract_patreon_creator(url)
    return f"https://www.patreon.com/c/{creator}/posts"


def patreon_story_key_url(url: str, chapter_regex: str | None) -> str:
    """Makes source_url unique per (creator, regex) so multiple stories can
    point at the same creator with different chapter filters (rule 6).
    Relies on URL fragments being ignored by Patreon URL parsing — confirm
    normalize_story_url() doesn't strip fragments before relying on this."""
    base = canonical_patreon_url(url)
    if not chapter_regex:
        return base
    digest = hashlib.md5(chapter_regex.encode("utf-8")).hexdigest()[:10]
    return f"{base}#cast={digest}"


async def _patreon_preview_metadata(
    url: str,
    engine: PatreonEngine,
    chapter_regex: str | None = None,
) -> MetadataPreview | None:
    if not _is_patreon_url(url):
        return None

    creator = _extract_patreon_creator(url)

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: engine.list_posts_with_access(url, story_match=chapter_regex),
        )
        creator = result.get("creator", creator)
        raw_posts = result.get("posts", [])
    except Exception as exc:
        logger.warning("Failed to fetch Patreon posts for preview: %s", exc)
        raw_posts = []

    chapters = [
        Chapter(
            number=p["number"],
            title=p["title"],
            selected=not p["locked"],
            locked=p["locked"],
        )
        for p in raw_posts
    ]

    locked_count = sum(1 for c in chapters if c.locked)
    if chapters:
        description = f"{len(chapters)} post(s) from {creator}"
        if locked_count:
            description += f" ({locked_count} locked — requires Patreon access)"
    else:
        description = f"Patreon creator page - visit {creator}'s Patreon to access all posts and rewards"

    return MetadataPreview(
        url=url,
        title=f"Patreon: {creator}",
        author=creator,
        subtitle=None,
        description=description,
        publish_year=None,
        language=None,
        series=None,
        genres=None,
        tags=None,
        chapter_count=len(chapters),
        chapters=chapters,
        story_site_id="patreon",
    )


@router.post("/preview")
async def preview_story_metadata(
    request: AddStoryRequest,
    download: StoryDownloadService = Depends(get_download),
    patreon_engine: PatreonEngine = Depends(get_patreon_engine),
) -> MetadataPreview:
    if _is_patreon_url(request.url):
        patreon_preview = await _patreon_preview_metadata(
            request.url, patreon_engine, chapter_regex=request.chapter_regex
        )
        if patreon_preview is not None:
            return patreon_preview

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
    download: StoryDownloadService = Depends(get_download),
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
    download_url = body.url

    if _is_patreon_url(body.url):
        creator = _extract_patreon_creator(body.url)
        download_url = patreon_story_key_url(body.url, body.chapter_regex)  # CHANGED

        existing = download.stories_repo.get_by_url(download_url)
        if existing:
            async with manager.job(job_id, f"Patreon: {creator}") as job:
                await job.update(
                    f"{creator}'s Patreon page (this filter) already added",
                    progress=100,
                )
            return

    async with manager.job(job_id, f"Adding '{title_hint}'") as job:
        await job.update("Downloading chapters…")

        story_id = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download.add_story(
                download_url,  # CHANGED — was body.url
                selected_chapters=body.selected_chapters,
                story_match=body.chapter_regex if _is_patreon_url(body.url) else None,
                content_source=body.content_source if _is_patreon_url(body.url) else None,
                filename_pattern=body.filename_pattern if _is_patreon_url(body.url) else None,
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
