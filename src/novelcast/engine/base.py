from abc import ABC, abstractmethod

KEY_TITLE = "title"
KEY_AUTHOR = "author"
KEY_URL = "url"
KEY_FILE_PATH = "file_path"
KEY_CHAPTERS = "chapters"
KEY_FORMAT = "format"
KEY_STORY_SITE_ID = "story_site_id"
KEY_RAW = "raw"

RESULT_KEYS = (
    KEY_TITLE,
    KEY_AUTHOR,
    KEY_URL,
    KEY_FILE_PATH,
    KEY_CHAPTERS,
    KEY_FORMAT,
    KEY_STORY_SITE_ID,
    KEY_RAW,
)

# Values that can go in the KEY_FORMAT field — one per engine. Shared here
# rather than defined per-engine so a typo doesn't silently produce a format
# string nothing else recognizes.
FORMAT_EPUB = "epub"
FORMAT_PATREON = "patreon"


def make_result(
    *,
    title=None,
    author=None,
    url=None,
    file_path=None,
    chapters=None,
    format=None,
    story_site_id=None,
    raw=None,
) -> dict:
    """Build a standard engine result dict. Every StoryEngine method that
    returns story data (fetch, check_updates) should build its return value
    through this, so callers can rely on every key always being present —
    even if it's None/empty for that particular engine/method.

    `chapters` is always a list of dicts shaped like:
        {"number": int, "title": str | None, "selected": bool, "raw": Any}
    Pass None if the engine/method doesn't produce chapter data — it'll
    normalize to [].
    """
    return {
        KEY_TITLE: title,
        KEY_AUTHOR: author,
        KEY_URL: url,
        KEY_FILE_PATH: file_path,
        KEY_CHAPTERS: chapters if chapters is not None else [],
        KEY_FORMAT: format,
        KEY_STORY_SITE_ID: story_site_id,
        KEY_RAW: raw if raw is not None else {},
    }


class StoryEngine(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str, progress_callback=None, output_dir="/temp") -> dict:
        """
        Must return a dict built via `make_result()` — i.e. it will always
        contain exactly: title, author, url, file_path, chapters, format,
        story_site_id, raw.
        """
        pass

    def check_updates(self, url: str) -> dict:
        """Same contract as fetch() — build the return value with make_result()."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support update checks")