# novelcast/api/routes/stories.py

from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from novelcast.api.deps import get_stories
from novelcast.services import StoryService

from .utils import require_admin

router = APIRouter(tags=["stories"])

_SOURCE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NovelCast/1.0)"}


def _first_image(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            value = element.get("content") or element.get("src")
            if value:
                return value
    return None


def _find_author_picture(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"royalroad.com", "www.royalroad.com", "patreon.com", "www.patreon.com"}:
        return None

    with httpx.Client(timeout=15, follow_redirects=True, headers=_SOURCE_HEADERS) as client:
        response = client.get(source_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        if hostname.endswith("royalroad.com"):
            profile = soup.select_one("a[href*='/profile/']")
            if profile and profile.get("href"):
                profile_response = client.get(urljoin(source_url, profile["href"]))
                profile_response.raise_for_status()
                soup = BeautifulSoup(profile_response.text, "html.parser")
            image = _first_image(
                soup,
                [
                    ".profile-avatar img",
                    ".profile-image img",
                    "img[alt*='avatar' i]",
                    "img[src*='profile' i]",
                    "meta[property='og:image']",
                ],
            )
        else:
            image = _first_image(
                soup,
                [
                    "img.avatar-image",
                    ".avatar-image img",
                    "img[class*='avatar-image']",
                    "meta[property='og:image']",
                    "meta[name='twitter:image']",
                    "img[alt*='profile' i]",
                ],
            )

    return urljoin(source_url, image) if image else None


# ── schemas ────────────────────────────────────────────────────────────────


class StoryMetadataUpdate(BaseModel):
    title: str
    author: str | None = None
    author_id: int | None = None
    subtitle: str | None = None
    description: str | None = None
    publish_year: int | None = None
    language: str | None = None
    series: list[str] | None = None
    genres: list[str] | None = None
    tags: list[str] | None = None
    source_url: str | None = None
    auto_update: bool | None = None
    hide_author_notes: bool | None = None


class AuthorUpdate(BaseModel):
    name: str
    bio: str | None = None
    picture_path: str | None = None
    links: list[dict] | None = None
    force: bool = False


class AuthorLinkItem(BaseModel):
    label: str
    url: str


class AuthorLinksUpdate(BaseModel):
    links: list[AuthorLinkItem]


class AuthorPictureFetch(BaseModel):
    source_url: str | None = None


class AuthorMerge(BaseModel):
    duplicate_ids: list[int]


@router.patch("/{story_id}/metadata")
def update_story_metadata(
    request: Request,
    story_id: int,
    body: StoryMetadataUpdate,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    if body.author and body.author_id:
        conflict = stories.find_author_collision(body.author, exclude_id=body.author_id)
        if conflict:
            raise HTTPException(
                status_code=409,
                detail={"conflict": conflict, "duplicate_id": body.author_id},
            )
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
            auto_update=body.auto_update,
            hide_author_notes=body.hide_author_notes,
        )
        request.app.state.ctx.emit("story_updated", {"story_id": story_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok", "story": updated}


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
    current_user: dict = Depends(require_admin),
):
    if not current_user or not current_user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")
    if not stories.get_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        stories.delete_story(story_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok"}


# ── author endpoints ───────────────────────────────────────────────────────


@router.get("/authors/{author_id}")
def get_author_detail(
    author_id: int,
    stories: StoryService = Depends(get_stories),
):
    author = stories.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return {"author": author}


@router.post("/authors/{author_id}/picture/fetch")
def fetch_author_picture(
    author_id: int,
    body: AuthorPictureFetch,
    stories: StoryService = Depends(get_stories),
):
    author = stories.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    source_url = body.source_url
    if not source_url:
        source_urls = [story.get("source_url") for story in author.get("stories", [])]
        source_url = next((url for url in source_urls if url), None)
    if not source_url:
        raise HTTPException(status_code=400, detail="No source story is available for this author")

    try:
        picture_url = _find_author_picture(source_url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch author picture: {e}") from e

    if not picture_url:
        raise HTTPException(status_code=404, detail="No author picture was found at the source")

    updated = stories.set_author_picture(author_id, picture_url)
    return {"status": "ok", "author": updated, "picture_url": picture_url}


@router.patch("/authors/{author_id}")
def update_author_detail(
    author_id: int,
    body: AuthorUpdate,
    stories: StoryService = Depends(get_stories),
):
    try:
        updated = stories.update_author(
            author_id,
            name=body.name,
            bio=body.bio,
            picture_path=body.picture_path,
            links=body.links,
            force=body.force,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if not updated:
        raise HTTPException(status_code=404, detail="Author not found")
    if "conflict" in updated:
        raise HTTPException(status_code=409, detail={"conflict": updated["conflict"]})
    return {"status": "ok", "author": updated}


@router.post("/authors/{author_id}/merge")
def merge_authors(
    author_id: int,
    body: AuthorMerge,
    stories: StoryService = Depends(get_stories),
):
    if not stories.get_author(author_id):
        raise HTTPException(status_code=404, detail="Author not found")
    try:
        merged = stories.merge_authors(author_id, body.duplicate_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok", "author": merged}


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
        updated = stories.update_author(
            author_id,
            name=body.name,
            bio=body.bio,
            picture_path=body.picture_path,
            links=body.links,
            force=body.force,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if not updated:
        raise HTTPException(status_code=404, detail="Author not found")
    if "conflict" in updated:
        raise HTTPException(status_code=409, detail={"conflict": updated["conflict"]})
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
