# novelcast/api/routes/api.py
from fastapi import APIRouter, Request

from novelcast.api.routes import (
    users,
    files,
    download,
    sync,
    admin,
    stories,
)

router = APIRouter()

router.include_router(users.router)
router.include_router(files.router)
router.include_router(download.router)
router.include_router(sync.router)
router.include_router(stories.router)

@router.get("/status")
def get_status(request: Request):
    return {
        "status": "ok",
        "db": "connected" if request.app.state.db else "missing",
    }

