from fastapi import APIRouter, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from novelcast.engine.updater import UpdateEngine
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────
# Global status
# ─────────────────────────────
status = {
    "downloading": False,
    "message": "",
    "progress": "",
}


# ─────────────────────────────
# Subscribe
# ─────────────────────────────
@router.post("/subscribe")
def subscribe(
    request: Request,
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    chapters: int = Form(1),
):
    db = request.app.state.db

    if not db.get_subscription(url):
        db.add_subscription(url, title=url)

    background_tasks.add_task(
        download_story_background,
        request,
        url,
        chapters,
    )

    return RedirectResponse("/", status_code=303)


# ─────────────────────────────
# Background download
# ─────────────────────────────
def download_story_background(request: Request, url: str, chapters: int):
    db = request.app.state.db
    engine = UpdateEngine(db)

    status["downloading"] = True
    status["message"] = "Downloading..."
    status["progress"] = "Starting"

    try:
        success, msg = engine.download_story(url, chapters)

        status["message"] = (
            "Download complete" if success else f"Failed: {msg}"
        )
        status["progress"] = "Done" if success else "Error"

    except Exception:
        logger.exception("Download error")
        status["message"] = "Unexpected error"
        status["progress"] = "Error"

    finally:
        status["downloading"] = False