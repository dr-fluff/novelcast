# novelcast/api/routes/pages/home.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from novelcast.api.deps import (
    get_current_user,
    get_progress,
    get_settings,
    get_stories,
    get_templates,
)
from novelcast.core.template_names import TemplateNames
from novelcast.core.template_context import TemplateContext as ContextKey
from novelcast.core.library_constants import (
    SORT_AUTHOR,
    SORT_CREATED,
    SORT_DIRECTION_ASCENDING,
    SORT_DIRECTION_DESCENDING,
    SORT_LAST_READ,
    SORT_LATEST_CHAPTER_UPDATED,
    SORT_SERIES,
    SORT_TITLE,
    SORT_UNREAD,
    SORT_YEAR,
)
from novelcast.services import ProgressService, SettingsService, StoryService

from .helpers import (
    default_sort_direction,
    enrich_story_progress,
    filter_stories,
    sort_stories,
    story_card,
    story_filter_options,
)
from .preferences import device_preference_key

router = APIRouter()
KEY = "key"
LABEL = "label"
DIRECTION_KEY = "direction"
ROUTE_PATH = "/"
USER_ID_KEY = "id"
EMPTY = ""
COMMA = ","
TRUE_QUERY_VALUE = "1"
DEVICE_ID_COOKIE = "novelcast_device_id"
LIBRARY_INDEX_PREFERENCE = "library.index"
CLEAR_LIBRARY_PREFERENCES_QUERY = "clear_library_preferences"
LIBRARY_IGNORE_PREFIXES_SETTING = "library.ignore_prefixes"
DEFAULT_IGNORE_PREFIXES = "the,a,an"

STATUS_NO_UNREAD = "no_unread"
STATUS_READ = "read"
STATUS_NOT_STARTED = "not_started"

SORT_DIRECTIONS = frozenset((SORT_DIRECTION_ASCENDING, SORT_DIRECTION_DESCENDING))

LABEL_TITLE = "Title"
LABEL_AUTHOR = "Author"
LABEL_SERIES = "Series"
LABEL_UNREAD_FIRST = "Unread first"
LABEL_LATEST_CHAPTER_UPDATED = "Latest chapter updated"
LABEL_LAST_READ = "Last read"
LABEL_DATE_ADDED = "Date added"
LABEL_PUBLISH_YEAR = "Publish year"
LABEL_ANY_STATUS = "Any status"
LABEL_HAS_UNREAD = "Has unread chapters"
LABEL_HAS_NO_UNREAD = "Has no unread chapters"
LABEL_ALL_DOWNLOADED_READ = "All downloaded read"
LABEL_NOT_STARTED = "Not started"

LIBRARY_STATE_QUERY_KEYS = (
    ContextKey.QUERY,
    ContextKey.SORT,
    ContextKey.SORT_DIRECTION,
    ContextKey.GENRE,
    ContextKey.TAG,
    ContextKey.SERIES,
    ContextKey.LANGUAGE,
    ContextKey.STATUS,
)

LIBRARY_SORT_OPTIONS = (
    {KEY: SORT_TITLE, LABEL: LABEL_TITLE, DIRECTION_KEY: SORT_DIRECTION_ASCENDING},
    {KEY: SORT_AUTHOR, LABEL: LABEL_AUTHOR, DIRECTION_KEY: SORT_DIRECTION_ASCENDING},
    {KEY: SORT_SERIES, LABEL: LABEL_SERIES, DIRECTION_KEY: SORT_DIRECTION_ASCENDING},
    {KEY: SORT_UNREAD, LABEL: LABEL_UNREAD_FIRST, DIRECTION_KEY: SORT_DIRECTION_ASCENDING},
    {KEY: SORT_LATEST_CHAPTER_UPDATED, LABEL: LABEL_LATEST_CHAPTER_UPDATED, DIRECTION_KEY: SORT_DIRECTION_DESCENDING},
    {KEY: SORT_LAST_READ, LABEL: LABEL_LAST_READ, DIRECTION_KEY: SORT_DIRECTION_DESCENDING},
    {KEY: SORT_CREATED, LABEL: LABEL_DATE_ADDED, DIRECTION_KEY: SORT_DIRECTION_DESCENDING},
    {KEY: SORT_YEAR, LABEL: LABEL_PUBLISH_YEAR, DIRECTION_KEY: SORT_DIRECTION_DESCENDING},
)

STATUS_OPTIONS = (
    {KEY: EMPTY, LABEL: LABEL_ANY_STATUS},
    {KEY: SORT_UNREAD, LABEL: LABEL_HAS_UNREAD},
    {KEY: STATUS_NO_UNREAD, LABEL: LABEL_HAS_NO_UNREAD},
    {KEY: STATUS_READ, LABEL: LABEL_ALL_DOWNLOADED_READ},
    {KEY: STATUS_NOT_STARTED, LABEL: LABEL_NOT_STARTED},
)

@router.get(ROUTE_PATH)
def home(
    request: Request,
    stories: StoryService = Depends(get_stories),
    progress: ProgressService = Depends(get_progress),
    settings: SettingsService = Depends(get_settings),
    current_user: dict | None = Depends(get_current_user),
    templates: Jinja2Templates = Depends(get_templates),
):
    preference_key = None
    device_id = request.cookies.get(DEVICE_ID_COOKIE)
    if current_user and device_id:
        preference_key = device_preference_key(device_id, LIBRARY_INDEX_PREFERENCE)

    if request.query_params.get(CLEAR_LIBRARY_PREFERENCES_QUERY) == TRUE_QUERY_VALUE:
        if current_user and preference_key:
            settings.delete_user_preference(current_user[USER_ID_KEY], preference_key)
        return RedirectResponse(ROUTE_PATH, status_code=303)

    saved_preferences = {}
    has_query_state = any(key in request.query_params for key in LIBRARY_STATE_QUERY_KEYS)
    if current_user and preference_key and not has_query_state:
        saved = settings.get_user_preference(current_user[USER_ID_KEY], preference_key, {})
        if isinstance(saved, dict):
            saved_preferences = saved

    query = request.query_params.get(ContextKey.QUERY, saved_preferences.get(ContextKey.QUERY, EMPTY)).strip().lower()
    sort = request.query_params.get(ContextKey.SORT, saved_preferences.get(ContextKey.SORT, SORT_TITLE))
    sort_direction = request.query_params.get(
        ContextKey.SORT_DIRECTION,
        saved_preferences.get(ContextKey.SORT_DIRECTION, default_sort_direction(sort)),
    )
    if sort_direction not in SORT_DIRECTIONS:
        sort_direction = default_sort_direction(sort)
    genre = request.query_params.get(ContextKey.GENRE, saved_preferences.get(ContextKey.GENRE, EMPTY)).strip()
    tag = request.query_params.get(ContextKey.TAG, saved_preferences.get(ContextKey.TAG, EMPTY)).strip()
    series = request.query_params.get(ContextKey.SERIES, saved_preferences.get(ContextKey.SERIES, EMPTY)).strip()
    language = request.query_params.get(ContextKey.LANGUAGE, saved_preferences.get(ContextKey.LANGUAGE, EMPTY)).strip()
    status = request.query_params.get(ContextKey.STATUS, saved_preferences.get(ContextKey.STATUS, EMPTY)).strip()

    # Parse ignore_prefixes from settings
    raw_prefixes = settings.get_server_setting(LIBRARY_IGNORE_PREFIXES_SETTING, default=DEFAULT_IGNORE_PREFIXES)
    ignore_prefixes = [prefix.strip() for prefix in raw_prefixes.split(COMMA) if prefix.strip()]

    all_stories = stories.get_all_stories()
    filter_options = story_filter_options(all_stories)
    progress_rows = progress.get_all_for_user(current_user[USER_ID_KEY]) if current_user else []
    all_stories = enrich_story_progress(all_stories, progress_rows)
    filtered_stories = filter_stories(
        all_stories,
        query,
        genre=genre,
        tag=tag,
        series=series,
        language=language,
        status=status,
        ignore_prefixes=ignore_prefixes,
    )
    sorted_stories = sort_stories(
        filtered_stories,
        sort,
        ignore_prefixes=ignore_prefixes,
        direction=sort_direction,
    )
    cards = [story_card(s) for s in sorted_stories]

    return templates.TemplateResponse(
        TemplateNames.INDEX,
        {
            ContextKey.REQUEST: request,
            ContextKey.STORIES: cards,
            ContextKey.SORT: sort,
            ContextKey.SORT_DIRECTION: sort_direction,
            ContextKey.QUERY: query,
            ContextKey.GENRE: genre,
            ContextKey.TAG: tag,
            ContextKey.SERIES: series,
            ContextKey.LANGUAGE: language,
            ContextKey.STATUS: status,
            ContextKey.FILTER_OPTIONS: filter_options,
            ContextKey.SORT_OPTIONS: LIBRARY_SORT_OPTIONS,
            ContextKey.STATUS_OPTIONS: STATUS_OPTIONS,
        },
    )
