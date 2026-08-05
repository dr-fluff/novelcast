# novelcast/api/routers/pages/__init__.py
from fastapi import APIRouter

from .account import router as account_router
from .admin_pages import router as admin_pages_router
from .authors import router as authors_router
from .chapter import router as chapter_router
from .home import router as home_router
from .preferences import router as preferences_router
from .search import router as search_router
from .settings import router as settings_router
from .stats import router as stats_router
from .story import router as story_router
from .offline_data import router as offline_router

router = APIRouter()

router.include_router(home_router)
router.include_router(story_router)
router.include_router(settings_router)
router.include_router(authors_router)
router.include_router(search_router)
router.include_router(chapter_router)
router.include_router(admin_pages_router)
router.include_router(preferences_router)
router.include_router(stats_router)
router.include_router(account_router)
router.include_router(offline_router)
