# novelcast/core/defaults.py

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
        KEY_DEFAULT: "info",
        KEY_OPTIONS: ["debug", "info", "warning", "error"],
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
# app
# ─────────────────────────────

APP_THEME = "theme"
APP_MAX_CONCURRENT_JOBS = "max_concurrent_jobs"
APP_DEFAULT_SORT = "default_sort"
APP_DEFAULT_CHAPTER_SORT = "default_chapter_sort"
APP_FONT_SIZE = "font_size"
APP_LINE_HEIGHT = "line_height"
APP_TIME_FORMAT = "time_format"
APP_DATE_FORMAT = "date_format"

APP_DEFAULTS = {
    APP_THEME: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Theme for the application",
        KEY_DEFAULT: "dark",
        KEY_OPTIONS: ["system", "light", "dark", "sepia"],
        KEY_LABEL: "Theme",
    },
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
        KEY_DEFAULT: "name",
        KEY_OPTIONS: ["name", "number"],
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
        KEY_DEFAULT: "24h",
        KEY_OPTIONS: ["24h", "12h"],
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
# fanficfare
# ─────────────────────────────

FFF_CONFIG_PATH = "config_path"
FFF_OUTPUT_FORMAT = "output_format"
FFF_INCLUDE_IMAGES = "include_images"
FFF_IS_ADULT = "is_adult"
FFF_LANGUAGE = "language"
FFF_TIMEOUT = "timeout"
FFF_RETRIES = "retries"
FFF_KEEP_SUMMARY_HTML = "keep_summary_html"
FFF_ROYALROAD_EMAIL = "royalroad_email"
FFF_ROYALROAD_PASSWORD = "royalroad_password"
FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME = "royalroad_slow_down_sleep_time"
FFF_TTHFANFIC_USERNAME = "tthfanfic_username"
FFF_TTHFANFIC_EMAIL = "tthfanfic_email"
FFF_TTHFANFIC_PASSWORD = "tthfanfic_password"

FANFICTIONFARE_DEFAULTS = {
    FFF_CONFIG_PATH: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Path to FanFicFare config file",
        KEY_DEFAULT: "config/fanficfare.ini",
        KEY_LABEL: "Config path",
    },
    FFF_OUTPUT_FORMAT: {
        KEY_TYPE: TYPE_SELECT,
        KEY_DESCRIPTION: "Default output format for FanFicFare",
        KEY_DEFAULT: "epub",
        KEY_OPTIONS: ["epub", "mobi", "html", "txt"],
        KEY_LABEL: "Output format",
        KEY_SCOPE: "defaults",
    },
    FFF_INCLUDE_IMAGES: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether to include images in the output",
        KEY_DEFAULT: True,
        KEY_LABEL: "Include images",
        KEY_SCOPE: "defaults",
    },
    FFF_IS_ADULT: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether the content is adult",
        KEY_DEFAULT: True,
        KEY_LABEL: "Adult content",
        KEY_SCOPE: "defaults",
    },
    FFF_LANGUAGE: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Default language for FanFicFare",
        KEY_DEFAULT: "en",
        KEY_LABEL: "Language",
        KEY_SCOPE: "defaults",
    },
    FFF_TIMEOUT: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Request timeout for FanFicFare (seconds)",
        KEY_DEFAULT: 60,
        KEY_MIN: 1,
        KEY_MAX: 300,
        KEY_LABEL: "Timeout (seconds)",
        KEY_SCOPE: "defaults",
    },
    FFF_RETRIES: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Number of retries for failed requests in FanFicFare",
        KEY_DEFAULT: 3,
        KEY_MIN: 0,
        KEY_MAX: 10,
        KEY_LABEL: "Retries",
        KEY_SCOPE: "defaults",
    },
    FFF_KEEP_SUMMARY_HTML: {
        KEY_TYPE: TYPE_BOOL,
        KEY_DESCRIPTION: "Whether to keep HTML in summaries",
        KEY_DEFAULT: True,
        KEY_LABEL: "Keep summary HTML",
        KEY_SCOPE: "epub",
    },
    FFF_ROYALROAD_EMAIL: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "E-mail for RoyalRoad",
        KEY_DEFAULT: "email@email.com",
        KEY_LABEL: "E-mail",
        KEY_SCOPE: "www.royalroad.com",
        KEY_INI_KEY: "e-mail",
    },
    FFF_ROYALROAD_PASSWORD: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: "Password for RoyalRoad",
        KEY_DEFAULT: "",
        KEY_LABEL: "Password",
        KEY_SCOPE: "www.royalroad.com",
        KEY_INI_KEY: "password",
    },
    FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME: {
        KEY_TYPE: TYPE_NUMBER,
        KEY_DESCRIPTION: "Sleep time between requests to RoyalRoad (seconds)",
        KEY_DEFAULT: 2,
        KEY_MIN: 1,
        KEY_MAX: 10,
        KEY_LABEL: "Slow down sleep time (seconds)",
        KEY_SCOPE: "www.royalroad.com",
    },
    FFF_TTHFANFIC_USERNAME: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "Username for TTHFanfic",
        KEY_DEFAULT: "Username",
        KEY_LABEL: "Username",
        KEY_SCOPE: "www.tthfanfic.org",
        KEY_INI_KEY: "username",
    },
    FFF_TTHFANFIC_EMAIL: {
        KEY_TYPE: TYPE_STRING,
        KEY_DESCRIPTION: "E-mail for TTHFanfic",
        KEY_DEFAULT: "email@email.com",
        KEY_LABEL: "E-mail",
        KEY_SCOPE: "www.tthfanfic.org",
        KEY_INI_KEY: "e-mail",
        KEY_LEGACY_KEY: "fanficfare.e-mail",
    },
    FFF_TTHFANFIC_PASSWORD: {
        KEY_TYPE: TYPE_SECRET,
        KEY_DESCRIPTION: "Password for TTHFanfic",
        KEY_DEFAULT: "",
        KEY_LABEL: "Password",
        KEY_SCOPE: "www.tthfanfic.org",
        KEY_INI_KEY: "password",
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
# section-name constants (for composing full "section.key" strings)
# ─────────────────────────────

SECTION_APP = "app"
SECTION_LIBRARY = "library"
SECTION_FANFICFARE = "fanficfare"
SECTION_SCRAPERS = "scrapers"
SECTION_RSS = "rss"
SECTION_DOWNLOADS = "downloads"
SECTION_LOGGING = "logging"
SECTION_TELEGRAM = "telegram"
SECTION_PATREON = "patreon"

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


"""
    ----------- User settings -------------
"""

# ─────────────────────────────
# user settings — field-name constants
# ─────────────────────────────

US_THEME = "theme"
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
# user settings — type/category/control constants
# ─────────────────────────────

US_TYPE_CHOICE = "choice"
US_TYPE_INT_RANGE = "int_range"
US_TYPE_FLOAT_RANGE = "float_range"
US_TYPE_BOOL = "bool"

US_CATEGORY_DISPLAY = "display"
US_CATEGORY_READING = "reading"

US_CONTROL_BUTTONS = "buttons"
US_CONTROL_SLIDER = "slider"


"""
    ----------- User settings -------------
"""

USER_SETTINGS_SCHEMA = {
    US_THEME: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: ("system", "light", "dark", "sepia"),
        KEY_DEFAULT: "system",
        KEY_CATEGORY: US_CATEGORY_DISPLAY,
    },
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
    US_CHAPTER_THEME: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: ("system", "light", "sepia", "dark"),
        KEY_DEFAULT: "system",
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Theme",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: "system", KEY_LABEL: "System", KEY_ICON: "fa-desktop"},
            {KEY_VALUE: "light", KEY_LABEL: "Light", KEY_ICON: "fa-sun"},
            {KEY_VALUE: "sepia", KEY_LABEL: "Sepia", KEY_ICON: "fa-book"},
            {KEY_VALUE: "dark", KEY_LABEL: "Dark", KEY_ICON: "fa-moon"},
        ],
    },
    US_CHAPTER_FONT_FAMILY: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: ("serif", "sans"),
        KEY_DEFAULT: "serif",
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Font Family",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: "sans", KEY_LABEL: "Sans"},
            {KEY_VALUE: "serif", KEY_LABEL: "Serif"},
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
        KEY_UNIT: "%",
        KEY_STEP: 5,
    },
    US_CHAPTER_FONT_WEIGHT: {
        KEY_TYPE: US_TYPE_CHOICE,
        KEY_CHOICES: (0, 1, 2),
        KEY_DEFAULT: 1,
        KEY_CATEGORY: US_CATEGORY_READING,
        KEY_LABEL: "Font Weight",
        KEY_CONTROL: US_CONTROL_BUTTONS,
        KEY_OPTIONS: [
            {KEY_VALUE: 0, KEY_LABEL: "Light"},
            {KEY_VALUE: 1, KEY_LABEL: "Normal"},
            {KEY_VALUE: 2, KEY_LABEL: "Bold"},
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
        KEY_UNIT: "%",
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
        KEY_UNIT: "rem",
        KEY_STEP: 1,
    },
}

REQUIRED_USER_SETTINGS = {US_THEME, US_FONT_SIZE, US_LINE_HEIGHT, US_AUTO_UPDATE}

""""
    ------------- Chapter patterns for titles -------------
"""

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
    r"\bchapter\s+(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|and|[-\s])+": "Chapter with written number (Chapter Ten, Chapter One Hundred and Twenty-One)",
    r"^\s*Day\s+(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|and)(?:[-\s]+(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|and))*\s*$": "Day with written number",
}
