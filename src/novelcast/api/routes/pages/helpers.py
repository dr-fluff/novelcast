from pathlib import Path
from urllib.parse import quote


def filter_stories(stories: list[dict], query: str) -> list[dict]:
    if not query:
        return stories

    query = query.lower()
    return [
        story for story in stories
        if query in (story.get("title") or "").lower()
        or query in (story.get("author") or "").lower()
    ]


def sort_stories(stories: list[dict], sort: str) -> list[dict]:
    if sort == "author":
        return sorted(stories, key=lambda s: (s.get("author") or "").lower())
    if sort == "downloaded":
        return sorted(stories, key=lambda s: s.get("downloaded_chapters", 0), reverse=True)
    return sorted(stories, key=lambda s: (s.get("title") or "").lower())


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
                    last_read_title = (
                        last_chapter.get("title")
                        or f"Chapter {last_chapter.get('chapter_number')}"
                    )
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
