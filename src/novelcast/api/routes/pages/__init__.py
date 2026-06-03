from fastapi import APIRouter

router = APIRouter(tags=["pages"])

from . import admin_pages, authors, chapter, home, settings, story, static, search  # noqa: F401
