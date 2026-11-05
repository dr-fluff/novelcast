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
HEATMAP_WEEKDAYS = ("Mon", "", "Wed", "", "Fri", "", "")


def build_heatmap_calendar(today: date, activity_by_date: dict[date, int], days: int = HEATMAP_DAYS) -> dict:
    start_date = today - timedelta(days=days - 1)
    calendar_start = start_date - timedelta(days=start_date.weekday())
    calendar_end = today + timedelta(days=6 - today.weekday())
    calendar_days = (calendar_end - calendar_start).days + 1

    heatmap_days = []
    heatmap_months = []
    for offset in range(calendar_days):
        current_date = calendar_start + timedelta(days=offset)
        is_padding = current_date < start_date or current_date > today
        heatmap_days.append(
            {
                "date": "" if is_padding else current_date.isoformat(),
                "seconds": 0 if is_padding else activity_by_date.get(current_date, 0),
                "is_padding": is_padding,
            }
        )

        if not is_padding and (current_date == start_date or current_date.day == 1):
            heatmap_months.append(
                {
                    "label": current_date.strftime("%b"),
                    "short_label": current_date.strftime("%b")[0],
                    "week": offset // 7,
                    "title": current_date.strftime("%B %Y"),
                }
            )

    range_label = f"{start_date.strftime('%b %Y')} - {today.strftime('%b %Y')}"
    return {
        "days": heatmap_days,
        "months": heatmap_months,
        "week_count": calendar_days // 7,
        "range_label": range_label,
    }


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

    calendar = build_heatmap_calendar(date.today(), activity_by_date)

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
            ContextKey.HEATMAP_DAYS: calendar["days"],
            "heatmap_months": calendar["months"],
            "heatmap_week_count": calendar["week_count"],
            "heatmap_range_label": calendar["range_label"],
            "heatmap_weekdays": HEATMAP_WEEKDAYS,
        },
    )
