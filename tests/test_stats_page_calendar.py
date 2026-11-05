from datetime import date

from novelcast.api.routes.pages.stats import build_heatmap_calendar


def test_heatmap_calendar_aligns_weekdays_and_labels_month_range():
    today = date(2026, 11, 5)
    active_day = date(2026, 11, 4)

    calendar = build_heatmap_calendar(today, {active_day: 900}, days=14)

    assert len(calendar["days"]) % 7 == 0
    assert calendar["week_count"] == len(calendar["days"]) // 7
    assert calendar["days"][0]["is_padding"] is True
    actual_days = [day for day in calendar["days"] if not day["is_padding"]]
    assert actual_days[-1]["date"] == today.isoformat()
    assert any(day["date"] == active_day.isoformat() and day["seconds"] == 900 for day in calendar["days"])
    assert calendar["range_label"] == "Oct 2026 - Nov 2026"


def test_heatmap_calendar_keeps_padding_days_inactive():
    calendar = build_heatmap_calendar(date(2026, 11, 5), {}, days=14)

    padding_days = [day for day in calendar["days"] if day["is_padding"]]
    assert padding_days
    assert all(day["date"] == "" and day["seconds"] == 0 for day in padding_days)