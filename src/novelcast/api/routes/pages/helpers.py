# novelcast/api/routes/pages/helpers.py
import logging
from urllib.parse import quote

import re
from bs4 import BeautifulSoup

from novelcast.core.library_constants import (
    SORT_CREATED,
    SORT_DIRECTION_ASCENDING,
    SORT_DIRECTION_DESCENDING,
    SORT_LAST_READ,
    SORT_LATEST_CHAPTER_UPDATED,
    SORT_YEAR,
)

logger = logging.getLogger(__name__)

DEFAULT_SORT_DIRECTIONS = {
    SORT_LATEST_CHAPTER_UPDATED: SORT_DIRECTION_DESCENDING,
    SORT_LAST_READ: SORT_DIRECTION_DESCENDING,
    SORT_CREATED: SORT_DIRECTION_DESCENDING,
    SORT_YEAR: SORT_DIRECTION_DESCENDING,
}


def default_sort_direction(sort: str) -> str:
    return DEFAULT_SORT_DIRECTIONS.get(sort, SORT_DIRECTION_ASCENDING)


def _norm(value) -> str:
    return str(value or "").strip().lower()


def _contains(values: list[str] | None, selected: str) -> bool:
    if not selected:
        return True
    selected = _norm(selected)
    return any(_norm(value) == selected for value in values or [])


def _story_latest_downloaded(story: dict) -> int:
    return int(story.get("latest_downloaded_chapter") or story.get("downloaded_chapters") or 0)


def story_has_unread(story: dict) -> bool:
    if not int(story.get("downloaded_chapters") or 0):
        return False
    last_read = int(story.get("last_read_chapter_number") or 0)
    return last_read < _story_latest_downloaded(story)


def story_has_not_unread(story: dict) -> bool:
    try:
        downloaded = int(story.get("downloaded_chapters") or 0)
        if downloaded <= 0:
            return False

        last_read = int(story.get("last_read_chapter_number") or 0)
        latest = int(_story_latest_downloaded(story) or 0)
        return last_read == latest

    except (TypeError, ValueError):
        logger.exception("Invalid story data: %s", story)
        return False


def build_story_view_model(story: dict, progress: dict | None, chapter_list: list[dict] | None = None) -> dict:
    # chapter_list must be the same title-filtered set the story page uses
    # (ChaptersService.list_by_story_filtered / list_by_stories_filtered),
    # not the raw downloaded_chapters count — otherwise numerator and
    # denominator here can disagree with the story page's regardless of how
    # the percentage math itself is written.
    chapter_list = chapter_list or []
    total = len(chapter_list)
    furthest_chapter_id = (progress or {}).get("furthest_chapter_id")
    chapters_read = sum(1 for c in chapter_list if furthest_chapter_id and c["id"] <= furthest_chapter_id)

    return {
        **story,
        # override with the filtered count so story_card's percent
        # calculation and the "N Chapters" display use the same set
        # the story page's percentage is based on
        "downloaded_chapters": total,
        # keep progress separate (IMPORTANT)
        "progress": {
            "last_read_chapter": chapters_read,
            "last_read_at": (progress or {}).get("updated_at"),
        },
        # derived UI state (single source of truth)
        "is_caught_up": total > 0 and chapters_read == total,
        "has_unread": total > 0 and chapters_read < total,
    }


def enrich_story_progress(
    stories: list[dict],
    progress_rows: list[dict],
    chapters_by_story: dict[int, list[dict]] | None = None,
) -> list[dict]:
    progress_by_story = {row["story_id"]: row for row in progress_rows}
    chapters_by_story = chapters_by_story or {}

    return [
        build_story_view_model(
            story,
            progress_by_story.get(story.get("id")),
            chapters_by_story.get(story.get("id"), []),
        )
        for story in stories
    ]


def filter_stories(
    stories: list[dict],
    query: str,
    genre: str = "",
    tag: str = "",
    series: str = "",
    language: str = "",
    status: str = "",
    ignore_prefixes: list[str] | None = None,  # ← new
) -> list[dict]:
    if not query:
        query = ""
    query = query.lower()
    prefixes = ignore_prefixes or []

    filtered = []
    for story in stories:
        title = story.get("title") or ""
        # Strip prefix from title before matching query
        normalized_title = _strip_prefix(title, prefixes).lower()
        haystack = " ".join(
            [
                normalized_title,
                story.get("author") or "",
                story.get("series") or "",
                story.get("genres") or "",
                story.get("tags") or "",
            ]
        ).lower()
        if query and query not in haystack:
            continue
        if not _contains(story.get("genres_list"), genre):
            continue
        if not _contains(story.get("tags_list"), tag):
            continue
        if not _contains(story.get("series_list"), series):
            continue
        if language and _norm(story.get("language")) != _norm(language):
            continue
        if status == "unread" and not story.get("has_unread"):
            continue
        if status == "read" and story.get("has_unread"):
            continue
        if status == "not_started" and story.get("last_read_chapter_number"):
            continue
        filtered.append(story)
    return filtered


def sort_stories(
    stories: list[dict],
    sort: str,
    ignore_prefixes: list[str] | None = None,  # ← new
    direction: str | None = None,
) -> list[dict]:
    prefixes = ignore_prefixes or []
    direction = direction if direction in {"asc", "desc"} else default_sort_direction(sort)
    reverse = direction == "desc"

    def title_key(story: dict) -> str:
        return _strip_prefix((story.get("title") or ""), prefixes).lower()

    def author_key(story: dict) -> str:
        return _strip_prefix((story.get("author") or ""), prefixes).lower()

    def date_key(story: dict, field: str):
        return story.get(field) is not None, story.get(field)

    if sort == "author":
        return sorted(stories, key=author_key, reverse=reverse)
    if sort == "downloaded":
        return sorted(stories, key=lambda s: s.get("downloaded_chapters", 0), reverse=reverse)
    if sort == "unread":
        return sorted(stories, key=lambda s: (not s.get("has_unread"), title_key(s)), reverse=reverse)
    if sort == "latest_chapter_updated":
        return sorted(stories, key=lambda s: date_key(s, "latest_chapter_updated_at"), reverse=reverse)
    if sort == "last_read":
        return sorted(stories, key=lambda s: date_key(s.get("progress") or {}, "last_read_at"), reverse=reverse)
    if sort == "updated":
        return sorted(stories, key=lambda s: date_key(s, "last_updated"), reverse=reverse)
    if sort == "created":
        return sorted(stories, key=lambda s: date_key(s, "created_at"), reverse=reverse)
    if sort == "year":
        return sorted(stories, key=lambda s: s.get("publish_year") or 0, reverse=reverse)
    if sort == "series":
        return sorted(
            stories,
            key=lambda s: _strip_prefix((s.get("series") or ""), prefixes).lower(),
            reverse=reverse,
        )
    return sorted(stories, key=title_key, reverse=reverse)


def story_filter_options(stories: list[dict]) -> dict[str, list[str]]:
    def unique(field: str) -> list[str]:
        values = {str(value).strip() for story in stories for value in story.get(field, []) if str(value).strip()}
        return sorted(values, key=str.lower)

    return {
        "genres": unique("genres_list"),
        "tags": unique("tags_list"),
        "series": unique("series_list"),
        "languages": sorted(
            {str(story.get("language")).strip() for story in stories if str(story.get("language") or "").strip()},
            key=str.lower,
        ),
    }


def story_card(story: dict) -> dict:
    title = story.get("title") or "Untitled"
    cover_path = story.get("cover_path")

    if cover_path and not cover_path.startswith(("http://", "https://", "/static/")):
        cover_url = f"/covers?path={quote(cover_path)}"
    else:
        cover_url = cover_path

    downloaded = story.get("downloaded_chapters", 0) or 0
    last_read = (story.get("progress") or {}).get("last_read_chapter", 0) or 0
    progress_percent = int(round((last_read / downloaded) * 100)) if downloaded else 0
    progress_percent = max(0, min(100, progress_percent))
    

    return {
        "id": story.get("id"),
        "display_title": title,
        "author": story.get("author"),
        "author_id": story.get("author_id"),
        "thumbnail_letter": title[0].upper() if title else "?",
        "last_chapter": story.get("downloaded_chapters", 0),
        "last_chapter_name": story.get("chapter"),
        "has_unread": story.get("has_unread", False),
        "is_caught_up": story.get("is_caught_up", False),
        "progress_percent": progress_percent,
        "genres": story.get("genres_list") or [],
        "tags": story.get("tags_list") or [],
        "series": story.get("series_list") or [],
        "cover_url": cover_url,
        "url": f"/story?story_id={story.get('id')}",
    }


def resolve_progress(
    user: dict | None,
    story_id: int,
    chapter_list: list[dict],
    progress,
    chapters=None,
    progress_row: dict | None = None,
) -> tuple[set[int], int | None, str | None]:
    read_chapters: set[int] = set()
    last_chapter_id = None
    last_read_title = None

    if user and user.get("id"):
        prog = progress_row if progress_row is not None else progress.get_progress(user["id"], story_id)
        if prog:
            last_chapter_id = prog.get("last_chapter_id")
            if last_chapter_id:
                last_chapter = next((chapter for chapter in chapter_list if chapter["id"] == last_chapter_id), None)
                if last_chapter is None and chapters is not None:
                    last_chapter = chapters.get_chapter(last_chapter_id)
                if last_chapter:
                    last_read_title = last_chapter.get("title") or f"Chapter {last_chapter.get('chapter_number')}"

            furthest_chapter_id = prog.get("furthest_chapter_id")
            if furthest_chapter_id:
                read_chapters = {c["id"] for c in chapter_list if c["id"] <= furthest_chapter_id}

    return read_chapters, last_chapter_id, last_read_title


def _format_duration(minutes: float) -> str:
    """Formats a minute count as 'X hr Y min', dropping whichever unit is zero."""
    total_minutes = int(round(minutes))
    hours, mins = divmod(total_minutes, 60)
    if hours and mins:
        return f"{hours} hr {mins} min"
    if hours:
        return f"{hours} hr"
    return f"{mins} min"

def progress_percent(chapter_list: list[dict], read_chapters: set[int], progress_row: dict | None, last_chapter_id: int | None) -> int:
    total_chapters = len(chapter_list)
    if not progress_row or not last_chapter_id or total_chapters <= 0:
        return None

    chapters_read = len(read_chapters)
    percent_complete = max(0, min(100, int(round((chapters_read / total_chapters) * 100))))
    return percent_complete


def build_reading_progress_card(
    chapter_list: list[dict],
    read_chapters: set[int],
    last_chapter_id: int | None,
    last_read_title: str | None,
    progress_row: dict | None,
    reading_speed_wpm: float | None,
) -> dict | None:
    percent_complete = progress_percent(chapter_list, read_chapters, progress_row, last_chapter_id)

    total_chapters = len(chapter_list)
    chapters_read = len(read_chapters)

    last_chapter_number = next(
        (c.get("chapter_number") for c in chapter_list if c["id"] == last_chapter_id),
        None,
    )

    unread_chapters = [c for c in chapter_list if c["id"] not in read_chapters]
    remaining_words = sum(c.get("word_count") or 0 for c in unread_chapters)
    has_full_word_data = bool(unread_chapters) and all(c.get("word_count") for c in unread_chapters)

    time_remaining_display = None
    if has_full_word_data and reading_speed_wpm and reading_speed_wpm > 0:
        time_remaining_display = _format_duration(remaining_words / reading_speed_wpm)

    return {
        "current_chapter_number": last_chapter_number,
        "current_chapter_title": last_read_title,
        "total_chapters": total_chapters,
        "chapters_read": chapters_read,
        "percent_complete": percent_complete,
        "last_read_at": progress_row.get("updated_at"),
        "time_remaining_display": time_remaining_display,
    }

def parse_settings_form(form: dict) -> tuple[dict, dict]:
    user_updates: dict = {}
    server_updates: dict = {}

    for key, value in form.items():
        if key.startswith("_") or "." not in key:
            continue

        if key.startswith("app."):
            user_updates[key[len("app."):]] = value
            continue

        if key.startswith("fanficfare.site."):
            remainder = key[len("fanficfare.site."):]
            domain, sep, field = remainder.rpartition(".")
            if not sep or not domain or not field:
                logger.warning("Malformed site override field name: %s", key)
                continue
            site_overrides = server_updates.setdefault("fanficfare", {}).setdefault("site_overrides", {})
            site_overrides.setdefault(domain, {})[field] = value
            continue

        section, _, field = key.partition(".")
        server_updates.setdefault(section, {})[field] = value

    return user_updates, server_updates


def _strip_prefix(title: str, prefixes: list[str]) -> str:
    """Return title with any leading ignore-prefix stripped, for sorting/searching."""
    lower = title.lower()
    for prefix in prefixes:
        p = prefix.strip().lower()
        if not p:
            continue
        if lower.startswith(p + " "):
            return title[len(p) :].strip()
    return title


def strip_duplicate_title_heading(html: str, chapter_title: str) -> str:
    if not html or not chapter_title:
        return html

    soup = BeautifulSoup(html, "html.parser")

    first_elem = None
    for child in soup.contents:
        if getattr(child, "name", None) is not None:
            first_elem = child
            break
        if str(child).strip():
            return html

    if first_elem is None or first_elem.name not in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return html

    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"^(chapter\s+)?(\d+|[ivxlcdm]+)?\s*[:\-.]?\s*", "", s)
        s = re.sub(r"\s+", " ", s)
        return s.strip()

    heading_text = normalize(first_elem.get_text())
    title_text = normalize(chapter_title)

    if heading_text == title_text or heading_text in title_text or title_text in heading_text:
        first_elem.decompose()

    return str(soup)
