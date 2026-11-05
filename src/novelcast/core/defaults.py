# novelcast/core/defaults.py
#
# Layout of this file:
#   1. Imports
#   2. Schema vocabulary   (KEY_*, TYPE_*)
#   3. Shared values       (scopes, option values, tab labels)
#   4. Section names       (SECTION_*)
#   5. Global settings     (one block per section: field names + defaults dict)
#   6. Settings registry   (SETTINGS, SETTINGS_TAB_LAYOUT)
#   7. User settings
#   8. Chapter title patterns

from novelcast.core.library_constants import (
    SORT_AUTHOR,
    SORT_CREATED,
    SORT_LAST_READ,
    SORT_LATEST_CHAPTER_UPDATED,
    SORT_SERIES,
    SORT_TITLE,
    SORT_UNREAD,
    SORT_YEAR,
)

# ═════════════════════════════════════════════════════════════
# 2. Schema vocabulary
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────
# Schema keys (the keys used inside each setting's dict)
# ─────────────────────────────

KEY_TYPE = "type"
KEY_DESCRIPTION = "description"
KEY_DEFAULT = "default"
KEY_MIN = "min"
KEY_MAX = "max"
KEY_LABEL = "label"
KEY_OPTIONS = "options"
KEY_SCOPE = "scope"
KEY_INI_KEY = "ini_key"
KEY_LEGACY_KEY = "legacy_key"
KEY_CHOICES = "choices"
KEY_CATEGORY = "category"
KEY_SUBCATEGORY = "subcategory"
KEY_CONTROL = "control"
KEY_UNIT = "unit"
KEY_STEP = "step"
KEY_VALUE = "value"
KEY_ICON = "icon"

# ─────────────────────────────
# Type constants (used as "type" values in the schema dicts below)
# ─────────────────────────────

TYPE_STRING = "string"
TYPE_BOOL = "bool"
TYPE_NUMBER = "number"
TYPE_INT = "int"
TYPE_SELECT = "select"
TYPE_SECRET = "secret"
TYPE_SITE_MAP = "site_map"

# ═════════════════════════════════════════════════════════════
# 3. Shared values
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────
# FanFicFare ini scopes (the ini section a setting is written to)
# ─────────────────────────────

SCOPE_DEFAULTS = "defaults"
SCOPE_EPUB = "epub"
SCOPE_ROYALROAD = "www.royalroad.com"
SCOPE_TTHFANFIC = "www.tthfanfic.org"

# ─────────────────────────────
# FanFicFare ini keys (shared between sites)
# ─────────────────────────────

INI_EMAIL = "e-mail"
INI_USERNAME = "username"
INI_PASSWORD = "password"

# ─────────────────────────────
# Option values: logging
# ─────────────────────────────

LOG_LEVEL_DEBUG = "debug"
LOG_LEVEL_INFO = "info"
LOG_LEVEL_WARNING = "warning"
LOG_LEVEL_ERROR = "error"

# ─────────────────────────────
# Option values: chapter sort
# ─────────────────────────────

CHAPTER_SORT_NAME = "name"
CHAPTER_SORT_NUMBER = "number"

# ─────────────────────────────
# Option values: time format
# ─────────────────────────────

TIME_FORMAT_24H = "24h"
TIME_FORMAT_12H = "12h"

# ─────────────────────────────
# Option values: FanFicFare output format
# ─────────────────────────────

OUTPUT_FORMAT_EPUB = "epub"
OUTPUT_FORMAT_MOBI = "mobi"
OUTPUT_FORMAT_HTML = "html"
OUTPUT_FORMAT_TXT = "txt"

# ─────────────────────────────
# Option values: reader theme / font family
# ─────────────────────────────

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_SEPIA = "sepia"
THEME_DARK = "dark"

FONT_FAMILY_SERIF = "serif"
FONT_FAMILY_SANS = "sans"

# ─────────────────────────────
# Settings-page tab categories / subcategories (display labels)
# ─────────────────────────────

TAB_CATEGORY_APP = "Appearance"
TAB_CATEGORY_LIBRARY = "Library"
TAB_CATEGORY_DOWNLOADS = "Downloads"
TAB_CATEGORY_SCRAPERS = "Sources"
TAB_CATEGORY_LOGGING = "System"
TAB_CATEGORY_WEBHOOKS = "Notifications"

TAB_SUBCATEGORY_GENERAL = "General"
TAB_SUBCATEGORY_DISPLAY = "Display"
TAB_SUBCATEGORY_LIBRARY_VIEW = "Library view"
TAB_SUBCATEGORY_STORAGE = "Storage"
TAB_SUBCATEGORY_UPDATES = "Updates"
TAB_SUBCATEGORY_LOGGING = "Logging"
TAB_SUBCATEGORY_FANFICFARE = "FanFicFare"
TAB_SUBCATEGORY_PROXY = "Proxy"
TAB_SUBCATEGORY_ROYALROAD = "RoyalRoad"
TAB_SUBCATEGORY_SCRIBBLEHUB = "ScribbleHub"
TAB_SUBCATEGORY_PATREON = "Patreon"
TAB_SUBCATEGORY_TTHFANFIC = "TTHFanfic"
TAB_SUBCATEGORY_TELEGRAM = "Telegram"

# Tab id that is not a settings section (RoyalRoad settings live in the
# fanficfare section but get their own tab).
TAB_ROYALROAD = "royalroad"
TAB_APP_DISPLAY = "app_display"
TAB_APP_LIBRARY_VIEW = "app_library_view"
TAB_APP_DOWNLOADS_GENERAL = "app_downloads_general"
TAB_LIBRARY_STORAGE = "library_storage"
TAB_LIBRARY_VIEW = "library_view"
TAB_LIBRARY_UPDATES = "library_updates"
TAB_FFF_PROXY = "fff_proxy"
TAB_FFF_TTHFANFIC = "fff_tthfanfic"
TAB_RSS_ROYALROAD = "rss_royalroad"
TAB_SCRAPERS_ROYALROAD = "scrapers_royalroad"
TAB_SCRAPERS_SCRIBBLEHUB = "scrapers_scribblehub"
TAB_SCRAPERS_PATREON = "scrapers_patreon"

# ═════════════════════════════════════════════════════════════
# 4. Section names (for composing full "section.key" strings)
# ═════════════════════════════════════════════════════════════

SECTION_APP = "app"
SECTION_LIBRARY = "library"
SECTION_FANFICFARE = "fanficfare"
SECTION_SCRAPERS = "scrapers"
SECTION_RSS = "rss"
SECTION_DOWNLOADS = "downloads"
SECTION_LOGGING = "logging"
SECTION_TELEGRAM = "telegram"
SECTION_PATREON = "patreon"

# ═════════════════════════════════════════════════════════════
# 5. Global settings
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────
# app
# ─────────────────────────────

APP_MAX_CONCURRENT_JOBS = "max_concurrent_jobs"
APP_DEFAULT_SORT = "default_sort"
APP_DEFAULT_CHAPTER_SORT = "default_chapter_sort"
APP_FONT_SIZE = "font_size"
APP_LINE_HEIGHT = "line_height"
APP_TIME_FORMAT = "time_format"
APP_DATE_FORMAT = "date_format"

APP_DEFAULTS = {
    APP_MAX_CONCURRENT_JOBS: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Maximum number of concurrent download jobs",
        KEY_DEFAULT: 3,
        KEY_MIN: 1,
        KEY_MAX: 10,
        KEY_LABEL: "Max concurrent jobs",
    },
    APP_DEFAULT_SORT: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Default sort order for the library",
        KEY_DEFAULT: SORT_TITLE,
        KEY_OPTIONS: [
            SORT_TITLE,
            SORT_AUTHOR,
            SORT_SERIES,
            SORT_UNREAD,
            SORT_LATEST_CHAPTER_UPDATED,
            SORT_LAST_READ,
            SORT_CREATED,
            SORT_YEAR,
        ],
        KEY_LABEL: "Default sort",
    },
    APP_DEFAULT_CHAPTER_SORT: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Default sort order for chapters",
        KEY_DEFAULT: CHAPTER_SORT_NAME,
        KEY_OPTIONS: [CHAPTER_SORT_NAME, CHAPTER_SORT_NUMBER],
        KEY_LABEL: "Chapter sort",
    },
    APP_FONT_SIZE: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default font size for the application",
        KEY_DEFAULT: "1em",
        KEY_LABEL: "Font size",
    },
    APP_LINE_HEIGHT: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default line height for the application",
        KEY_DEFAULT: "1.5em",
        KEY_LABEL: "Line height",
    },
    APP_TIME_FORMAT: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Default time format for the application",
        KEY_DEFAULT: TIME_FORMAT_24H,
        KEY_OPTIONS: [TIME_FORMAT_24H, TIME_FORMAT_12H],
        KEY_LABEL: "Time format",
    },
    APP_DATE_FORMAT: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default date format for the application (strftime format)",
        KEY_DEFAULT: "%Y-%m-%d",
        KEY_LABEL: "Date format",
    },
}

# ─────────────────────────────
# library
# ─────────────────────────────

LIBRARY_DATA_PATH = "data_path"
LIBRARY_DATABASE_PATH = "database_path"
LIBRARY_AUTO_UPDATE = "auto_update"
LIBRARY_UPDATE_INTERVAL_HOURS = "update_interval_hours"
LIBRARY_UPDATE_ON_STARTUP = "update_on_startup"
LIBRARY_UPDATE_TIME = "update_time"
LIBRARY_IGNORE_PREFIXES = "ignore_prefixes"

LIBRARY_DEFAULTS = {
    LIBRARY_DATA_PATH: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Path to the library data directory",
        KEY_DEFAULT: "data/",
        KEY_LABEL: "Data path",
    },
    LIBRARY_DATABASE_PATH: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Path to the library database file",
        KEY_DEFAULT: "data/novelcast.db",
        KEY_LABEL: "Database path",
    },
    LIBRARY_AUTO_UPDATE: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Automatically check books in the library for new chapters",
        KEY_DEFAULT: True,
        KEY_LABEL: "Automatic sync",
    },
    LIBRARY_UPDATE_INTERVAL_HOURS: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "How often automatic checks for new chapters run",
        KEY_DEFAULT: 24,
        KEY_MIN: 1,
        KEY_MAX: 168,
        KEY_LABEL: "Sync frequency (hours)",
    },
    LIBRARY_UPDATE_ON_STARTUP: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Run an automatic check when NovelCast starts",
        KEY_DEFAULT: False,
        KEY_LABEL: "Sync on startup",
    },
    LIBRARY_UPDATE_TIME: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Time of day to check for updates (HH:MM, 24h format)",
        KEY_DEFAULT: "02:00",
        KEY_LABEL: "Update time",
    },
    LIBRARY_IGNORE_PREFIXES: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Comma-separated list of prefixes to ignore when sorting novels (e.g. 'the,a,an')",
        KEY_DEFAULT: "the,a,an",
        KEY_LABEL: "Ignore prefixes",
    },
}

# ─────────────────────────────
# downloads
# ─────────────────────────────

DOWNLOADS_PATH = "path"

DOWNLOAD_DEFAULTS = {
    DOWNLOADS_PATH: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default download path for novels",
        KEY_DEFAULT: "downloads",
        KEY_LABEL: "Download path",
    },
}

# ─────────────────────────────
# fanficfare
# ─────────────────────────────

# General
FFF_CONFIG_PATH = "config_path"
FFF_OUTPUT_FORMAT = "output_format"
FFF_INCLUDE_IMAGES = "include_images"
FFF_IS_ADULT = "is_adult"
FFF_LANGUAGE = "language"
FFF_TIMEOUT = "timeout"
FFF_CONNECT_TIMEOUT = "connect_timeout"
FFF_RETRIES = "retries"
FFF_KEEP_SUMMARY_HTML = "keep_summary_html"

# RoyalRoad
FFF_ROYALROAD_EMAIL = "royalroad_email"
FFF_ROYALROAD_PASSWORD = "royalroad_password"
FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME = "royalroad_slow_down_sleep_time"
FFF_ROYAL_ROAD_FLARESOLVERR_PROXY = "royalroad_flaresolverr_proxy"
FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_ADDRESS = "royalroad_flaresolverr_proxy_address"
FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_PORT = "royalroad_flaresolverr_proxy_port"
FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_PROTOCOL = "royalroad_flaresolverr_proxy_protocol"
FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_TIMEOUT = "royalroad_flaresolverr_proxy_timeout"
FFF_ROYAL_ROAD_FLARESOLVERR_USE_SESSION = "royalroad_flaresolverr_use_session"
FFF_ROYAL_ROAD_FLARESOLVERR_SESSION = "royalroad_flaresolverr_session"

# TTHFanfic
FFF_TTHFANFIC_USERNAME = "tthfanfic_username"
FFF_TTHFANFIC_EMAIL = "tthfanfic_email"
FFF_TTHFANFIC_PASSWORD = "tthfanfic_password"

FANFICTIONFARE_DEFAULTS = {
    # ── General ──────────────────
    FFF_CONFIG_PATH: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Path to FanFicFare config file",
        KEY_DEFAULT: "config/fanficfare.ini",
        KEY_LABEL: "Config path",
    },
    FFF_OUTPUT_FORMAT: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Default output format for FanFicFare",
        KEY_DEFAULT: OUTPUT_FORMAT_EPUB,
        KEY_OPTIONS: [
            OUTPUT_FORMAT_EPUB,
            OUTPUT_FORMAT_MOBI,
            OUTPUT_FORMAT_HTML,
            OUTPUT_FORMAT_TXT,
        ],
        KEY_LABEL: "Output format",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_INCLUDE_IMAGES: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether to include images in the output",
        KEY_DEFAULT: True,
        KEY_LABEL: "Include images",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_IS_ADULT: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether the content is adult",
        KEY_DEFAULT: True,
        KEY_LABEL: "Adult content",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_LANGUAGE: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default language for FanFicFare",
        KEY_DEFAULT: "en",
        KEY_LABEL: "Language",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_TIMEOUT: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Request timeout for FanFicFare (seconds)",
        KEY_DEFAULT: 240,
        KEY_MIN: 1,
        KEY_MAX: 300,
        KEY_LABEL: "Timeout (seconds)",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_CONNECT_TIMEOUT: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Connection timeout for FanFicFare (seconds)",
        KEY_DEFAULT: 120,
        KEY_MIN: 1,
        KEY_MAX: 300,
        KEY_LABEL: "Connect timeout (seconds)",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_RETRIES: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Number of retries for failed requests in FanFicFare",
        KEY_DEFAULT: 3,
        KEY_MIN: 0,
        KEY_MAX: 10,
        KEY_LABEL: "Retries",
        KEY_SCOPE: SCOPE_DEFAULTS,
    },
    FFF_KEEP_SUMMARY_HTML: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether to keep HTML in summaries",
        KEY_DEFAULT: True,
        KEY_LABEL: "Keep summary HTML",
        KEY_SCOPE: SCOPE_EPUB,
    },
    # ── RoyalRoad ────────────────
    FFF_ROYALROAD_EMAIL: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "E-mail for RoyalRoad",
        KEY_DEFAULT: "email@email.com",
        KEY_LABEL: "E-mail",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: INI_EMAIL,
    },
    FFF_ROYALROAD_PASSWORD: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: "Password for RoyalRoad",
        KEY_DEFAULT: "",
        KEY_LABEL: "Password",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: INI_PASSWORD,
    },
    FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Sleep time between requests to RoyalRoad (seconds)",
        KEY_DEFAULT: 2,
        KEY_MIN: 1,
        KEY_MAX: 10,
        KEY_LABEL: "Slow down sleep time (seconds)",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "royalroad_slow_down_sleep_time",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_PROXY: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Proxy for FlareSolverr when accessing RoyalRoad",
        KEY_DEFAULT: True,
        KEY_LABEL: "FlareSolverr Proxy",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "use_flaresolverr_proxy",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_ADDRESS: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Proxy address for FlareSolverr when accessing RoyalRoad",
        KEY_DEFAULT: "192.168.1.103",
        KEY_LABEL: "FlareSolverr Proxy Address",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "flaresolverr_proxy_address",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_PORT: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Proxy port for FlareSolverr when accessing RoyalRoad",
        KEY_DEFAULT: "8191",
        KEY_MIN: 0,
        KEY_MAX: 65535,
        KEY_LABEL: "FlareSolverr Proxy Port",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "flaresolverr_proxy_port",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_PROTOCOL: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Proxy protocol for FlareSolverr when accessing RoyalRoad (http, https, socks5, etc.)",
        KEY_DEFAULT: "http",
        KEY_LABEL: "FlareSolverr Proxy Protocol",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "flaresolverr_proxy_protocol",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_PROXY_TIMEOUT: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Maximum time FlareSolverr spends solving a request (seconds)",
        KEY_DEFAULT: 180,
        KEY_MIN: 1,
        KEY_MAX: 300,
        KEY_LABEL: "FlareSolverr Proxy Timeout (seconds)",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "flaresolverr_proxy_timeout",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_USE_SESSION: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Reuse a FlareSolverr browser session for RoyalRoad requests",
        KEY_DEFAULT: True,
        KEY_LABEL: "Reuse FlareSolverr session",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "use_flaresolverr_session",
    },
    FFF_ROYAL_ROAD_FLARESOLVERR_SESSION: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "FlareSolverr browser session name",
        KEY_DEFAULT: "FanFicFareSession",
        KEY_LABEL: "FlareSolverr session name",
        KEY_SCOPE: SCOPE_ROYALROAD,
        KEY_INI_KEY: "flaresolverr_session",
    },
    # ── TTHFanfic ────────────────
    FFF_TTHFANFIC_USERNAME: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Username for TTHFanfic",
        KEY_DEFAULT: "Username",
        KEY_LABEL: "Username",
        KEY_SCOPE: SCOPE_TTHFANFIC,
        KEY_INI_KEY: INI_USERNAME,
    },
    FFF_TTHFANFIC_EMAIL: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "E-mail for TTHFanfic",
        KEY_DEFAULT: "email@email.com",
        KEY_LABEL: "E-mail",
        KEY_SCOPE: SCOPE_TTHFANFIC,
        KEY_INI_KEY: INI_EMAIL,
        KEY_LEGACY_KEY: "fanficfare.e-mail",
    },
    FFF_TTHFANFIC_PASSWORD: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: "Password for TTHFanfic",
        KEY_DEFAULT: "",
        KEY_LABEL: "Password",
        KEY_SCOPE: SCOPE_TTHFANFIC,
        KEY_INI_KEY: INI_PASSWORD,
        KEY_LEGACY_KEY: "fanficfare.password",
    },
}

# ─────────────────────────────
# scrapers
# ─────────────────────────────

SCRAPERS_ROYALROAD_ENABLED = "royalroad_enabled"
SCRAPERS_SCRIBBLEHUB_ENABLED = "scribblehub_enabled"
SCRAPERS_PATREON_ENABLED = "patreon_enabled"

SCRAPER_DEFAULTS = {
    SCRAPERS_ROYALROAD_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Enable searching/scraping RoyalRoad",
        KEY_DEFAULT: True,
        KEY_LABEL: "Enable RoyalRoad",
    },
    SCRAPERS_SCRIBBLEHUB_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Enable searching/scraping ScribbleHub",
        KEY_DEFAULT: False,
        KEY_LABEL: "Enable ScribbleHub",
    },
    SCRAPERS_PATREON_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Enable searching/scraping Patreon",
        KEY_DEFAULT: False,
        KEY_LABEL: "Enable Patreon",
    },
}

# ─────────────────────────────
# rss
# ─────────────────────────────

RSS_ENABLED = "enabled"
RSS_INTERVAL = "interval"
RSS_ROYALROAD = "royalroad"

RSS_DEFAULTS = {
    RSS_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DEFAULT: True,
        KEY_LABEL: "Enable RSS polling",
    },
    RSS_INTERVAL: {
        KEY_TYPE: TYPE_INT,
        KEY_DEFAULT: 10,
        KEY_LABEL: "Polling interval (minutes)",
        KEY_MIN: 1,
        KEY_MAX: 1440,
    },
    RSS_ROYALROAD: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DEFAULT: True,
        KEY_LABEL: "Enable Royal Road RSS",
    },
}

# ─────────────────────────────
# logging
# ─────────────────────────────

LOGGING_LEVEL = "level"
LOGGING_FILE = "file"
LOGGING_MAX_BYTES = "max_bytes"
LOGGING_TAIL_BUFFER_SIZE = "tail_buffer_size"
LOGGING_NOISY_LOGGERS = "noisy_loggers"
LOGGING_MAX_AMOUNT_OF_FILES = "max_amount_of_files"

LOGGING_DEFAULTS = {
    LOGGING_LEVEL: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Log verbosity level",
        KEY_DEFAULT: LOG_LEVEL_INFO,
        KEY_OPTIONS: [
            LOG_LEVEL_DEBUG,
            LOG_LEVEL_INFO,
            LOG_LEVEL_WARNING,
            LOG_LEVEL_ERROR,
        ],
        KEY_LABEL: "Log level",
    },
    LOGGING_FILE: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Log file path (relative to app root, leave empty for console only)",
        KEY_DEFAULT: "logs/novelcast.log",
        KEY_LABEL: "Log file",
    },
    LOGGING_MAX_BYTES: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Maximum log file size before rotation (bytes)",
        KEY_DEFAULT: 10485760,  # 10 MB
        KEY_MIN: 1048576,  # 1 MB
        KEY_MAX: 104857600,  # 100 MB
        KEY_LABEL: "Max file size (bytes)",
    },
    LOGGING_TAIL_BUFFER_SIZE: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Number of recent log lines kept in memory for the live log viewer",
        KEY_DEFAULT: 500,
        KEY_MIN: 50,
        KEY_MAX: 5000,
        KEY_LABEL: "Live tail buffer (lines)",
    },
    LOGGING_NOISY_LOGGERS: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "JSON array of logger names to suppress to WARNING level",
        KEY_DEFAULT: (
            '["websockets","websockets.server","websockets.protocol",'
            '"websockets.client","uvicorn","uvicorn.access",'
            '"uvicorn.protocols","uvicorn.protocols.websockets",'
            '"uvicorn.protocols.websockets.websockets_impl",'
            '"asyncio","httpx","httpcore","multipart","python_multipart","starlette"]'
        ),
        KEY_LABEL: "Suppressed loggers (JSON)",
    },
    LOGGING_MAX_AMOUNT_OF_FILES: {
        KEY_TYPE: TYPE_INT,
        KEY_DESCRIPTION: "How many log files are going to be saved",
        KEY_DEFAULT: 20,
        KEY_LABEL: "Amount of saved log files",
    },
}

# ─────────────────────────────
# telegram
# ─────────────────────────────

TELEGRAM_ENABLED = "enabled"
TELEGRAM_BOT_TOKEN = "bot_token"
TELEGRAM_CHAT_ID = "chat_id"

TELEGRAM_DEFAULTS = {
    TELEGRAM_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Enable Telegram bot integration",
        KEY_DEFAULT: False,
        KEY_LABEL: "Enable Telegram",
    },
    TELEGRAM_BOT_TOKEN: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: "Telegram Bot API token (from @BotFather)",
        KEY_DEFAULT: "",
        KEY_LABEL: "Bot Token",
    },
    TELEGRAM_CHAT_ID: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Telegram chat ID to send messages to",
        KEY_DEFAULT: "",
        KEY_LABEL: "Chat ID",
    },
}

# ─────────────────────────────
# patreon
# ─────────────────────────────

PATREON_ENABLED = "enabled"
PATREON_SESSION_COOKIE = "session_cookie"

PATREON_DEFAULTS = {
    PATREON_ENABLED: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Enable Patreon integration",
        KEY_DEFAULT: False,
        KEY_LABEL: "Enable Patreon",
    },
    PATREON_SESSION_COOKIE: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: (
            "Log into patreon.com in your browser. Then:\n"
            "Chrome/Edge: press F12 to open Developer Tools, click the "
            "'Application' tab, expand 'Cookies' in the left sidebar, click "
            "'https://www.patreon.com', find the row named 'session_id', "
            "and copy its Value.\n"
            "Firefox: press F12, click the 'Storage' tab, expand 'Cookies', "
            "click 'https://www.patreon.com', find 'session_id', and copy "
            "its Value.\n"
            "Paste that value here."
        ),
        KEY_DEFAULT: "",
        KEY_LABEL: "Session Cookie",
    },
}

# ═════════════════════════════════════════════════════════════
# 6. Settings registry
# ═════════════════════════════════════════════════════════════

SETTINGS = {
    SECTION_APP: APP_DEFAULTS,
    SECTION_LIBRARY: LIBRARY_DEFAULTS,
    SECTION_FANFICFARE: FANFICTIONFARE_DEFAULTS,
    SECTION_SCRAPERS: SCRAPER_DEFAULTS,
    SECTION_RSS: RSS_DEFAULTS,
    SECTION_DOWNLOADS: DOWNLOAD_DEFAULTS,
    SECTION_LOGGING: LOGGING_DEFAULTS,
    SECTION_TELEGRAM: TELEGRAM_DEFAULTS,
    SECTION_PATREON: PATREON_DEFAULTS,
}

# Settings-page grouping by tab id. Add a section here to place it under an
# existing category, or give it a new category and optional subcategory.
SETTINGS_TAB_LAYOUT = {
    TAB_APP_DISPLAY: {KEY_CATEGORY: TAB_CATEGORY_APP, KEY_SUBCATEGORY: TAB_SUBCATEGORY_DISPLAY},
    TAB_APP_LIBRARY_VIEW: {KEY_CATEGORY: TAB_CATEGORY_APP, KEY_SUBCATEGORY: TAB_SUBCATEGORY_LIBRARY_VIEW},
    TAB_LIBRARY_VIEW: {KEY_CATEGORY: TAB_CATEGORY_APP, KEY_SUBCATEGORY: TAB_SUBCATEGORY_LIBRARY_VIEW},
    TAB_LIBRARY_STORAGE: {KEY_CATEGORY: TAB_CATEGORY_LIBRARY, KEY_SUBCATEGORY: TAB_SUBCATEGORY_STORAGE},
    TAB_LIBRARY_UPDATES: {KEY_CATEGORY: TAB_CATEGORY_LIBRARY, KEY_SUBCATEGORY: TAB_SUBCATEGORY_UPDATES},
    SECTION_RSS: {KEY_CATEGORY: TAB_CATEGORY_LIBRARY, KEY_SUBCATEGORY: TAB_SUBCATEGORY_UPDATES},
    TAB_APP_DOWNLOADS_GENERAL: {KEY_CATEGORY: TAB_CATEGORY_DOWNLOADS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_GENERAL},
    SECTION_DOWNLOADS: {KEY_CATEGORY: TAB_CATEGORY_DOWNLOADS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_GENERAL},
    SECTION_FANFICFARE: {KEY_CATEGORY: TAB_CATEGORY_DOWNLOADS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_FANFICFARE},
    TAB_FFF_PROXY: {KEY_CATEGORY: TAB_CATEGORY_DOWNLOADS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_PROXY},
    TAB_SCRAPERS_ROYALROAD: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_ROYALROAD},
    TAB_RSS_ROYALROAD: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_ROYALROAD},
    TAB_ROYALROAD: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_ROYALROAD},
    TAB_SCRAPERS_SCRIBBLEHUB: {
        KEY_CATEGORY: TAB_CATEGORY_SCRAPERS,
        KEY_SUBCATEGORY: TAB_SUBCATEGORY_SCRIBBLEHUB,
    },
    TAB_SCRAPERS_PATREON: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_PATREON},
    SECTION_PATREON: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_PATREON},
    TAB_FFF_TTHFANFIC: {KEY_CATEGORY: TAB_CATEGORY_SCRAPERS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_TTHFANFIC},
    SECTION_TELEGRAM: {KEY_CATEGORY: TAB_CATEGORY_WEBHOOKS, KEY_SUBCATEGORY: TAB_SUBCATEGORY_TELEGRAM},
    SECTION_LOGGING: {KEY_CATEGORY: TAB_CATEGORY_LOGGING, KEY_SUBCATEGORY: TAB_SUBCATEGORY_LOGGING},
}

# ═════════════════════════════════════════════════════════════
# 7. User settings
# ═════════════════════════════════════════════════════════════

# ─────────────────────────────
# Field-name constants
# ─────────────────────────────

US_FONT_SIZE = "font_size"
US_LINE_HEIGHT = "line_height"
US_AUTO_UPDATE = "auto_update"
US_CHAPTER_THEME = "chapter_theme"
US_CHAPTER_FONT_FAMILY = "chapter_font_family"
US_CHAPTER_FONT_SIZE = "chapter_font_size"
US_CHAPTER_LINE_SPACING = "chapter_line_spacing"
US_CHAPTER_FONT_WEIGHT = "chapter_font_weight"
US_CHAPTER_PARAGRAPH_SPACING = "chapter_paragraph_spacing"
US_CHAPTER_CONTENT_PADDING = "chapter_content_padding"

# ─────────────────────────────
# Type / category / control constants
# ─────────────────────────────

US_TYPE_CHOICE = "choice"
US_TYPE_INT_RANGE = "int_range"
US_TYPE_FLOAT_RANGE = "float_range"
US_TYPE_BOOL = "bool"

US_CATEGORY_DISPLAY = "display"
US_CATEGORY_READING = "reading"

US_CONTROL_BUTTONS = "buttons"
US_CONTROL_SLIDER = "slider"

# ─────────────────────────────
# Units / icons
# ─────────────────────────────

US_UNIT_PERCENT = "%"
US_UNIT_REM = "rem"

ICON_SYSTEM = "fa-desktop"
ICON_LIGHT = "fa-sun"
ICON_SEPIA = "fa-book"
ICON_DARK = "fa-moon"

# ─────────────────────────────
# Font weight values
# ─────────────────────────────

FONT_WEIGHT_LIGHT = 0
FONT_WEIGHT_NORMAL = 1
FONT_WEIGHT_BOLD = 2

# ─────────────────────────────
# Schema
# ─────────────────────────────

USER_SETTINGS_SCHEMA = {
    # ── Display ──────────────────
    US_FONT_SIZE: {
        KEY_TYPE: US_TYPE_INT_RANGE,
        KEY_MIN: 10,
        KEY_MAX: 30,
        KEY_DEFAULT: 14,
        KEY_CATEGORY: US_CATEGORY_DISPLAY,
    },
    US_LINE_HEIGHT: {
        KEY_TYPE: US_TYPE_FLOAT_RANGE,
        KEY_MIN: 1.0,
        KEY_MAX: 2.5,
        KEY_DEFAULT: 1.5,
        KEY_CATEGORY: US_CATEGORY_DISPLAY,
    },
    US_AUTO_UPDATE: {
        KEY_TYPE: US_TYPE_BOOL,
        KEY_DEFAULT: False,
        KEY_CATEGORY: US_CATEGORY_DISPLAY,
    },
    # ── Reading ──────────────────
    US_CHAPTER_THEME: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: (THEME_SYSTEM, THEME_LIGHT, THEME_SEPIA, THEME_DARK),
        KEY_DEFAULT: THEME_SYSTEM,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Theme",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: THEME_SYSTEM, KEY_LABEL: "System", KEY_ICON: ICON_SYSTEM},
            {KEY_VALUE: THEME_LIGHT, KEY_LABEL: "Light", KEY_ICON: ICON_LIGHT},
            {KEY_VALUE: THEME_SEPIA, KEY_LABEL: "Sepia", KEY_ICON: ICON_SEPIA},
            {KEY_VALUE: THEME_DARK, KEY_LABEL: "Dark", KEY_ICON: ICON_DARK},
        ],
    },
    US_CHAPTER_FONT_FAMILY: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: (FONT_FAMILY_SERIF, FONT_FAMILY_SANS),
        KEY_DEFAULT: FONT_FAMILY_SERIF,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Font Family",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: FONT_FAMILY_SANS, KEY_LABEL: "Sans"},
            {KEY_VALUE: FONT_FAMILY_SERIF, KEY_LABEL: "Serif"},
        ],
    },
    US_CHAPTER_FONT_SIZE: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: (75, 88, 100, 113, 125, 150, 225),
        KEY_DEFAULT: 100,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Font Size",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: 75, KEY_LABEL: "12"},
            {KEY_VALUE: 88, KEY_LABEL: "14"},
            {KEY_VALUE: 100, KEY_LABEL: "16"},
            {KEY_VALUE: 113, KEY_LABEL: "18"},
            {KEY_VALUE: 125, KEY_LABEL: "20"},
            {KEY_VALUE: 150, KEY_LABEL: "24"},
            {KEY_VALUE: 225, KEY_LABEL: "36"},
        ],
    },
    US_CHAPTER_LINE_SPACING: {
        KEY_TYPE: US_TYPE_INT_RANGE,
        KEY_MIN: 50,
        KEY_MAX: 150,
        KEY_DEFAULT: 100,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Line Spacing",
        KEY_CONTROL: US_CONTROL_SLIDER,
        KEY_UNIT: US_UNIT_PERCENT,
        KEY_STEP: 5,
    },
    US_CHAPTER_FONT_WEIGHT: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: (FONT_WEIGHT_LIGHT, FONT_WEIGHT_NORMAL, FONT_WEIGHT_BOLD),
        KEY_DEFAULT: FONT_WEIGHT_NORMAL,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Font Weight",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: FONT_WEIGHT_LIGHT, KEY_LABEL: "Light"},
            {KEY_VALUE: FONT_WEIGHT_NORMAL, KEY_LABEL: "Normal"},
            {KEY_VALUE: FONT_WEIGHT_BOLD, KEY_LABEL: "Bold"},
        ],
    },
    US_CHAPTER_PARAGRAPH_SPACING: {
        KEY_TYPE: US_TYPE_INT_RANGE,
        KEY_MIN: 0,
        KEY_MAX: 200,
        KEY_DEFAULT: 100,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Paragraph Spacing",
        KEY_CONTROL: US_CONTROL_SLIDER,
        KEY_UNIT: US_UNIT_PERCENT,
        KEY_STEP: 5,
    },
    US_CHAPTER_CONTENT_PADDING: {
        KEY_TYPE: US_TYPE_INT_RANGE,
        KEY_MIN: 3,
        KEY_MAX: 20,
        KEY_DEFAULT: 3,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Margin",
        KEY_CONTROL: US_CONTROL_SLIDER,
        KEY_UNIT: US_UNIT_REM,
        KEY_STEP: 1,
    },
}

REQUIRED_USER_SETTINGS = {US_FONT_SIZE, US_LINE_HEIGHT, US_AUTO_UPDATE}

# ═════════════════════════════════════════════════════════════
# 8. Chapter title patterns
# ═════════════════════════════════════════════════════════════

# Number words shared by the "written number" patterns below.
_NUMBER_WORDS = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million"
)

DEFAULT_CHAPTER_PATTERNS: dict[str, str] = {
    r"^(\d+)\s*[-–—‑−]": "Leading number (53 —, 102 —)",
    r"\bchapter\s*:?\s*(\d+)": "Chapter format (Chapter 1, Chapter: 1)",
    r"\bchapter\s*\?+": "Unknown chapter (Chapter ???)",
    r"\bch\.?\s*(\d+)": "Short form (Ch. 42, Ch42)",
    r"^\[?(\d+\.\d+)": "Decimal format (1.1, 3.10, [1.1])",
    r"^\[?(\d+)\.": "Simple numbering (1. Title, [1. Title])",
    r"\bpart\s*(\d+)": "Part numbering (Part 1, Part 9)",
    r"\bpart\s+[ivxlcdm]+\b": "Roman numeral parts (Part IV)",
    r"\bprologue\b": "Prologue",
    r"\bepilogue\b": "Epilogue",
    r"\binterlude\b": "Interlude",
    r"\bafterword\b": "Afterword",
    r"\bglossary\b": "Glossary",
    r"\bappendix\b": "Appendix",
    r"\bcover\b": "Cover page",
    r"\bby\s+\w+": "Author attribution",
    r"\w.*\s+(\d+)\s*[-–—‑−]": "Text with trailing number (In Search of Harmony 26 —)",
    r"^\s*ch\.?\s*(\d+)\b(?:\s*[-–—-−]?\s*.*)?$": "CH format (CH7, CH13- Title, CH1 Prologue)",
    rf"\bchapter\s+(?:{_NUMBER_WORDS}|and|[-\s])+": "Chapter with written number (Chapter Ten, Chapter One Hundred and Twenty-One)",
    rf"^\s*Day\s+(?:{_NUMBER_WORDS}|billion|and)(?:[-\s]+(?:{_NUMBER_WORDS}|billion|and))*\s*$": "Day with written number",
}