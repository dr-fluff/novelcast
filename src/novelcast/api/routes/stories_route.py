# novelcast/api/routes/stories.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from novelcast.api.deps import get_stories
from novelcast.services import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


# ── schemas ───────────────────────────────────────────────────────────────

class StoryMetadataUpdate(BaseModel):
    title: str
    author: str | None = None
    source_url: str | None = None


class AuthorUpdate(BaseModel):
    name: str
    bio: str | None = None
    profile_url: str | None = None


# ── endpoints ─────────────────────────────────────────────────────────────

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
    """
    Update story title, author (denormalized text), and source URL.
    Also upserts the Author row and links it via story_author.
    """
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        updated = stories.update_story_metadata(
            story_id=story_id,
            title=body.title,
            author=body.author,
            source_url=body.source_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {"status": "ok", "story": updated}


@router.get("/{story_id}/authors")
def get_story_authors(
    story_id: int,
    stories: StoryService = Depends(get_stories),
):
    """Return all Author rows linked to this story."""
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    authors = stories.get_story_authors(story_id)
    return {"authors": authors}


@router.patch("/{story_id}/authors/{author_id}")
def update_story_author(
    story_id: int,
    author_id: int,
    body: AuthorUpdate,
    stories: StoryService = Depends(get_stories),
):
    """Update an Author record linked to this story."""
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        updated = stories.update_author(
            author_id=author_id,
            name=body.name,
            bio=body.bio,
            profile_url=body.profile_url,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not updated:
        raise HTTPException(status_code=404, detail="Author not found")

    return {"status": "ok", "author": updated}
