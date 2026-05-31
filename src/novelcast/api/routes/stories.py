# novelcast/api/routes/stories.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from novelcast.api.deps import get_stories
from novelcast.services import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


# ── schemas ────────────────────────────────────────────────────────────────

class StoryMetadataUpdate(BaseModel):
    title: str
    author: str | None = None
    subtitle: str | None = None
    description: str | None = None
    publish_year: int | None = None
    language: str | None = None
    series: list[str] | None = None
    genres: list[str] | None = None
    tags: list[str] | None = None
    source_url: str | None = None


class AuthorUpdate(BaseModel):
    name: str
    bio: str | None = None


class AuthorLinkItem(BaseModel):
    label: str
    url: str


class AuthorLinksUpdate(BaseModel):
    links: list[AuthorLinkItem]


# ── story endpoints ────────────────────────────────────────────────────────

@router.get("/{story_id}")
def get_story(
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    story = stories.get_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"story": story}


@router.delete("/{story_id}")
def delete_story(
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        stories.delete_story(story_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok"}


@router.patch("/{story_id}/metadata")
def update_story_metadata(
    story_id: int,
    body: StoryMetadataUpdate,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        updated = stories.update_story_metadata(
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
            source_url=body.source_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok", "story": updated}


# ── author endpoints ───────────────────────────────────────────────────────

@router.get("/{story_id}/authors")
def get_story_authors(
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    return {"authors": stories.get_story_authors(story_id)}


@router.patch("/{story_id}/authors/{author_id}")
def update_story_author(
    story_id: int,
    author_id: int,
    body: AuthorUpdate,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        updated = stories.update_author(author_id, name=body.name, bio=body.bio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if not updated:
        raise HTTPException(status_code=404, detail="Author not found")
    return {"status": "ok", "author": updated}


@router.put("/{story_id}/authors/{author_id}/links")
def set_author_links(
    story_id: int,
    author_id: int,
    body: AuthorLinksUpdate,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        saved = stories.set_author_links(
            author_id,
            [{"label": lnk.label, "url": lnk.url} for lnk in body.links],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok", "links": saved}

