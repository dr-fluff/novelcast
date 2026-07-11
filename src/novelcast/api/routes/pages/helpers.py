# novelcast/api/routes/pages/helpers.py
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


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


def build_story_view_model(story: dict, progress: dict | None) -> dict:
    last_read = int((progress or {}).get("last_chapter_number") or 0)
    latest = int(_story_latest_downloaded(story) or 0)
    downloaded = int(story.get("downloaded_chapters") or 0)

    return {
        **story,
        # keep progress separate (IMPORTANT)
        "progress": {
            "last_read_chapter": last_read,
        },
        # derived UI state (single source of truth)
        "is_caught_up": downloaded > 0 and last_read == latest,
        "has_unread": downloaded > 0 and last_read < latest,
    }


def enrich_story_progress(stories: list[dict], progress_rows: list[dict]) -> list[dict]:
    progress_by_story = {row["story_id"]: row for row in progress_rows}

    return [build_story_view_model(story, progress_by_story.get(story.get("id"))) for story in stories]


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
) -> list[dict]:
    prefixes = ignore_prefixes or []

    def title_key(story: dict) -> str:
        return _strip_prefix((story.get("title") or ""), prefixes).lower()

    def author_key(story: dict) -> str:
        return _strip_prefix((story.get("author") or ""), prefixes).lower()

    def date_key(story: dict, field: str):
        return story.get(field) is not None, story.get(field)

    if sort == "author":
        return sorted(stories, key=author_key)
    if sort == "downloaded":
        return sorted(stories, key=lambda s: s.get("downloaded_chapters", 0), reverse=True)
    if sort == "unread":
        return sorted(stories, key=lambda s: (not s.get("has_unread"), title_key(s)))
    if sort == "updated":
        return sorted(stories, key=lambda s: date_key(s, "last_updated"), reverse=True)
    if sort == "created":
        return sorted(stories, key=lambda s: date_key(s, "created_at"), reverse=True)
    if sort == "year":
        return sorted(stories, key=lambda s: s.get("publish_year") or 0, reverse=True)
    if sort == "series":
        return sorted(
            stories,
            key=lambda s: _strip_prefix((s.get("series") or ""), prefixes).lower(),
        )
    return sorted(stories, key=title_key)


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

    return {
        "id": story.get("id"),
        "display_title": title,
        "author": story.get("author"),
        "thumbnail_letter": title[0].upper() if title else "?",
        "last_chapter": story.get("downloaded_chapters", 0),
        "last_chapter_name": story.get("chapter"),
        "has_unread": story.get("has_unread", False),
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
    chapters,
) -> tuple[set[int], int | None, str | None]:
    read_chapters: set[int] = set()
    last_chapter_id = None
    last_read_title = None

    if user and user.get("id"):
        prog = progress.get_progress(user["id"], story_id)
        if prog:
            last_chapter_id = prog.get("last_chapter_id")
            if last_chapter_id:
                last_chapter = chapters.get_chapter(last_chapter_id)
                if last_chapter:
                    last_read_title = last_chapter.get("title") or f"Chapter {last_chapter.get('chapter_number')}"
                read_chapters = {c["id"] for c in chapter_list if c["id"] <= last_chapter_id}

    return read_chapters, last_chapter_id, last_read_title


def parse_settings_form(form: dict) -> tuple[dict, dict]:
    user_updates: dict = {}
    server_updates: dict = {}

    for key, value in form.items():
        if key.startswith("_") or "." not in key:
            continue

        parts = key.split(".")

        if parts[0] == "app":
            user_updates[".".join(parts[1:])] = value
            continue

        section = parts[0]
        if section not in server_updates:
            server_updates[section] = {}

        current = server_updates[section]
        if len(parts) >= 3:
            domain = parts[1]
            field = parts[2]
            current.setdefault(domain, {})
            current[domain][field] = value
        else:
            field = parts[1]
            current[field] = value

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
