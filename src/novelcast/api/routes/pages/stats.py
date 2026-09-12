# novelcast/api/routes/pages/stats.py
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import get_current_user, get_stats, get_templates
from novelcast.core.template_names import TemplateNames
from novelcast.core.template_context import TemplateContext as ContextKey
from novelcast.services import StatsService

router = APIRouter()

# Number of days shown in the activity heatmap (GitHub's is 371 —
# 53 weeks — so the grid always ends on a full week).
HEATMAP_DAYS = 371


@router.get("/stats")
def stats_page(
    request: Request,
    stats: StatsService = Depends(get_stats),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    if not current_user:
        return RedirectResponse("/login", status_code=303)

    user_id = current_user["id"]
    summary = stats.get_summary(user_id)

    activity_rows = stats.get_activity_heatmap(user_id, days=HEATMAP_DAYS)
    activity_by_date = {row["date"]: row["read_seconds"] for row in activity_rows}

    today = date.today()
    heatmap_days = []
    for offset in range(HEATMAP_DAYS - 1, -1, -1):
        d = today - timedelta(days=offset)
        heatmap_days.append(
            {
                "date": d.isoformat(),
                "seconds": activity_by_date.get(d, 0),
            }
        )

    total_read_seconds = summary["total_read_seconds"]
    reading_speed_wpm = summary["reading_speed_wpm"]

    return templates.TemplateResponse(
        TemplateNames.STATS,
        {
            ContextKey.REQUEST: request,
            ContextKey.CURRENT_USER: current_user,
            ContextKey.TOTAL_READ_HOURS: round(total_read_seconds / 3600, 1),
            ContextKey.DEVICE_COUNT: summary["device_count"],
            ContextKey.CHAPTERS_READ: summary["chapters_read"],
            ContextKey.STORIES_READ: summary["stories_read"],
            ContextKey.READING_SPEED_WPM: round(reading_speed_wpm) if reading_speed_wpm is not None else None,
            ContextKey.HEATMAP_DAYS: heatmap_days,
        },
    )
