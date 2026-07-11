# novelcast/core/defaults.py


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
        "type": TYPE_STRING,
        "description": "Path to the library data directory",
        "default": "data/",
        "label": "Data path",
    },
    LIBRARY_DATABASE_PATH: {
        "type": TYPE_STRING,
        "description": "Path to the library database file",
        "default": "data/novelcast.db",
        "label": "Database path",
    },
    LIBRARY_AUTO_UPDATE: {
        "type": TYPE_BOOL,
        "description": "Automatically check books in the library for new chapters",
        "default": True,
        "label": "Automatic sync",
    },
    LIBRARY_UPDATE_INTERVAL_HOURS: {
        "type": TYPE_NUMBER,
        "description": "How often automatic checks for new chapters run",
        "default": 24,
        "min": 1,
        "max": 168,
        "label": "Sync frequency (hours)",
    },
    LIBRARY_UPDATE_ON_STARTUP: {
        "type": TYPE_BOOL,
        "description": "Run an automatic check when NovelCast starts",
        "default": False,
        "label": "Sync on startup",
    },
    LIBRARY_UPDATE_TIME: {
        "type": TYPE_STRING,
        "description": "Time of day to check for updates (HH:MM, 24h format)",
        "default": "02:00",
        "label": "Update time",
    },
    LIBRARY_IGNORE_PREFIXES: {
        "type": TYPE_STRING,
        "description": "Comma-separated list of prefixes to ignore when sorting novels (e.g. 'the,a,an')",
        "default": "the,a,an",
        "label": "Ignore prefixes",
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
        "type": TYPE_SELECT,
        "description": "Log verbosity level",
        "default": "info",
        "options": ["debug", "info", "warning", "error"],
        "label": "Log level",
    },
    LOGGING_FILE: {
        "type": TYPE_STRING,
        "description": "Log file path (relative to app root, leave empty for console only)",
        "default": "logs/novelcast.log",
        "label": "Log file",
    },
    LOGGING_MAX_BYTES: {
        "type": TYPE_NUMBER,
        "description": "Maximum log file size before rotation (bytes)",
        "default": 10485760,  # 10 MB
        "min": 1048576,  # 1 MB
        "max": 104857600,  # 100 MB
        "label": "Max file size (bytes)",
    },
    LOGGING_TAIL_BUFFER_SIZE: {
        "type": TYPE_NUMBER,
        "description": "Number of recent log lines kept in memory for the live log viewer",
        "default": 500,
        "min": 50,
        "max": 5000,
        "label": "Live tail buffer (lines)",
    },
    LOGGING_NOISY_LOGGERS: {
        "type": TYPE_STRING,
        "description": "JSON array of logger names to suppress to WARNING level",
        "default": (
            '["websockets","websockets.server","websockets.protocol",'
            '"websockets.client","uvicorn","uvicorn.access",'
            '"uvicorn.protocols","uvicorn.protocols.websockets",'
            '"uvicorn.protocols.websockets.websockets_impl",'
            '"asyncio","httpx","httpcore","multipart","python_multipart","starlette"]'
        ),
        "label": "Suppressed loggers (JSON)",
    },
    LOGGING_MAX_AMOUNT_OF_FILES: {
        "type": TYPE_INT,
        "description": "How many log files are going to be saved",
        "default": 20,
        "label": "Amount of saved log files",
    },
}

# ─────────────────────────────
# downloads
# ─────────────────────────────

DOWNLOADS_PATH = "path"

DOWNLOAD_DEFAULTS = {
    DOWNLOADS_PATH: {
        "type": TYPE_STRING,
        "description": "Default download path for novels",
        "default": "downloads",
        "label": "Download path",
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
        "type": TYPE_SELECT,
        "description": "Default theme for the application",
        "default": "dark",
        "options": ["light", "dark", "sepia"],
        "label": "Theme",
    },
    APP_MAX_CONCURRENT_JOBS: {
        "type": TYPE_NUMBER,
        "description": "Maximum number of concurrent download jobs",
        "default": 3,
        "min": 1,
        "max": 10,
        "label": "Max concurrent jobs",
    },
    APP_DEFAULT_SORT: {
        "type": TYPE_SELECT,
        "description": "Default sort order for the library",
        "default": "title",
        "options": [
            "title",
            "author",
            "downloaded",
            "total_chapters",
            "last_updated",
            "created_at",
        ],
        "label": "Default sort",
    },
    APP_DEFAULT_CHAPTER_SORT: {
        "type": TYPE_SELECT,
        "description": "Default sort order for chapters",
        "default": "name",
        "options": ["name", "number"],
        "label": "Chapter sort",
    },
    APP_FONT_SIZE: {
        "type": TYPE_STRING,
        "description": "Default font size for the application",
        "default": "1em",
        "label": "Font size",
    },
    APP_LINE_HEIGHT: {
        "type": TYPE_STRING,
        "description": "Default line height for the application",
        "default": "1.5em",
        "label": "Line height",
    },
    APP_TIME_FORMAT: {
        "type": TYPE_SELECT,
        "description": "Default time format for the application",
        "default": "24h",
        "options": ["24h", "12h"],
        "label": "Time format",
    },
    APP_DATE_FORMAT: {
        "type": TYPE_STRING,
        "description": "Default date format for the application (strftime format)",
        "default": "%Y-%m-%d",
        "label": "Date format",
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
        "type": TYPE_STRING,
        "description": "Path to FanFicFare config file",
        "default": "config/fanficfare.ini",
        "label": "Config path",
    },
    FFF_OUTPUT_FORMAT: {
        "type": TYPE_SELECT,
        "description": "Default output format for FanFicFare",
        "default": "epub",
        "options": ["epub", "mobi", "html", "txt"],
        "label": "Output format",
        "scope": "defaults",
    },
    FFF_INCLUDE_IMAGES: {
        "type": TYPE_BOOL,
        "description": "Whether to include images in the output",
        "default": True,
        "label": "Include images",
        "scope": "defaults",
    },
    FFF_IS_ADULT: {
        "type": TYPE_BOOL,
        "description": "Whether the content is adult",
        "default": True,
        "label": "Adult content",
        "scope": "defaults",
    },
    FFF_LANGUAGE: {
        "type": TYPE_STRING,
        "description": "Default language for FanFicFare",
        "default": "en",
        "label": "Language",
        "scope": "defaults",
    },
    FFF_TIMEOUT: {
        "type": TYPE_NUMBER,
        "description": "Request timeout for FanFicFare (seconds)",
        "default": 60,
        "min": 1,
        "max": 300,
        "label": "Timeout (seconds)",
        "scope": "defaults",
    },
    FFF_RETRIES: {
        "type": TYPE_NUMBER,
        "description": "Number of retries for failed requests in FanFicFare",
        "default": 3,
        "min": 0,
        "max": 10,
        "label": "Retries",
        "scope": "defaults",
    },
    FFF_KEEP_SUMMARY_HTML: {
        "type": TYPE_BOOL,
        "description": "Whether to keep HTML in summaries",
        "default": True,
        "label": "Keep summary HTML",
        "scope": "epub",
    },
    FFF_ROYALROAD_EMAIL: {
        "type": TYPE_STRING,
        "description": "E-mail for RoyalRoad",
        "default": "email@email.com",
        "label": "E-mail",
        "scope": "www.royalroad.com",
        "ini_key": "e-mail",
    },
    FFF_ROYALROAD_PASSWORD: {
        "type": TYPE_SECRET,
        "description": "Password for RoyalRoad",
        "default": "",
        "label": "Password",
        "scope": "www.royalroad.com",
        "ini_key": "password",
    },
    FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME: {
        "type": TYPE_NUMBER,
        "description": "Sleep time between requests to RoyalRoad (seconds)",
        "default": 2,
        "min": 1,
        "max": 10,
        "label": "Slow down sleep time (seconds)",
        "scope": "www.royalroad.com",
    },
    FFF_TTHFANFIC_USERNAME: {
        "type": TYPE_STRING,
        "description": "Username for TTHFanfic",
        "default": "Username",
        "label": "Username",
        "scope": "www.tthfanfic.org",
        "ini_key": "username",
    },
    FFF_TTHFANFIC_EMAIL: {
        "type": TYPE_STRING,
        "description": "E-mail for TTHFanfic",
        "default": "email@email.com",
        "label": "E-mail",
        "scope": "www.tthfanfic.org",
        "ini_key": "e-mail",
        "legacy_key": "fanficfare.e-mail",
    },
    FFF_TTHFANFIC_PASSWORD: {
        "type": TYPE_SECRET,
        "description": "Password for TTHFanfic",
        "default": "",
        "label": "Password",
        "scope": "www.tthfanfic.org",
        "ini_key": "password",
        "legacy_key": "fanficfare.password",
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
        "type": TYPE_BOOL,
        "description": "Enable searching/scraping RoyalRoad",
        "default": True,
        "label": "Enable RoyalRoad",
    },
    SCRAPERS_SCRIBBLEHUB_ENABLED: {
        "type": TYPE_BOOL,
        "description": "Enable searching/scraping ScribbleHub",
        "default": False,
        "label": "Enable ScribbleHub",
    },
    SCRAPERS_PATREON_ENABLED: {
        "type": TYPE_BOOL,
        "description": "Enable searching/scraping Patreon",
        "default": False,
        "label": "Enable Patreon",
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
        "type": TYPE_BOOL,
        "description": "Enable Telegram bot integration",
        "default": False,
        "label": "Enable Telegram",
    },
    TELEGRAM_BOT_TOKEN: {
        "type": TYPE_SECRET,
        "description": "Telegram Bot API token (from @BotFather)",
        "default": "",
        "label": "Bot Token",
    },
    TELEGRAM_CHAT_ID: {
        "type": TYPE_STRING,
        "description": "Telegram chat ID to send messages to",
        "default": "",
        "label": "Chat ID",
    },
}

# ─────────────────────────────
# patreon
# ─────────────────────────────

PATREON_ENABLED = "enabled"
PATREON_SESSION_COOKIE = "session_cookie"

PATREON_DEFAULTS = {
    PATREON_ENABLED: {
        "type": TYPE_BOOL,
        "description": "Enable Patreon integration",
        "default": False,
        "label": "Enable Patreon",
    },
    PATREON_SESSION_COOKIE: {
        "type": TYPE_SECRET,
        "description": (
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
        "default": "",
        "label": "Session Cookie",
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
        "type": TYPE_BOOL,
        "default": True,
        "label": "Enable RSS polling",
    },
    RSS_INTERVAL: {
        "type": TYPE_INT,
        "default": 10,
        "label": "Polling interval (minutes)",
        "min": 1,
        "max": 1440,
    },
    RSS_ROYALROAD: {
        "type": TYPE_BOOL,
        "default": True,
        "label": "Enable Royal Road RSS",
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

# left as-is below (unchanged from your version) — say the word if you want
# USER_SETTINGS_SCHEMA and DEFAULT_CHAPTER_PATTERNS constant-ified too, same pattern.

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
        "type": US_TYPE_CHOICE,
        "choices": ("light", "dark"),
        "default": "light",
        "category": US_CATEGORY_DISPLAY,
    },
    US_FONT_SIZE: {
        "type": US_TYPE_INT_RANGE,
        "min": 10,
        "max": 30,
        "default": 14,
        "category": US_CATEGORY_DISPLAY,
    },
    US_LINE_HEIGHT: {
        "type": US_TYPE_FLOAT_RANGE,
        "min": 1.0,
        "max": 2.5,
        "default": 1.5,
        "category": US_CATEGORY_DISPLAY,
    },
    US_AUTO_UPDATE: {
        "type": US_TYPE_BOOL,
        "default": False,
        "category": US_CATEGORY_DISPLAY,
    },
    US_CHAPTER_THEME: {
        "type": US_TYPE_CHOICE,
        "choices": ("light", "sepia", "dark"),
        "default": "light",
        "category": US_CATEGORY_READING,
        "label": "Theme",
        "control": US_CONTROL_BUTTONS,
        "options": [
            {"value": "light", "label": "Light", "icon": "fa-sun"},
            {"value": "sepia", "label": "Sepia", "icon": "fa-book"},
            {"value": "dark", "label": "Dark", "icon": "fa-moon"},
        ],
    },
    US_CHAPTER_FONT_FAMILY: {
        "type": US_TYPE_CHOICE,
        "choices": ("serif", "sans"),
        "default": "serif",
        "category": US_CATEGORY_READING,
        "label": "Font Family",
        "control": US_CONTROL_BUTTONS,
        "options": [
            {"value": "sans", "label": "Sans"},
            {"value": "serif", "label": "Serif"},
        ],
    },
    US_CHAPTER_FONT_SIZE: {
        "type": US_TYPE_CHOICE,
        "choices": (75, 88, 100, 113, 125, 150, 225),
        "default": 100,
        "category": US_CATEGORY_READING,
        "label": "Font Size",
        "control": US_CONTROL_BUTTONS,
        "options": [
            {"value": 75, "label": "12"},
            {"value": 88, "label": "14"},
            {"value": 100, "label": "16"},
            {"value": 113, "label": "18"},
            {"value": 125, "label": "20"},
            {"value": 150, "label": "24"},
            {"value": 225, "label": "36"},
        ],
    },
    US_CHAPTER_LINE_SPACING: {
        "type": US_TYPE_INT_RANGE,
        "min": 50,
        "max": 150,
        "default": 100,
        "category": US_CATEGORY_READING,
        "label": "Line Spacing",
        "control": US_CONTROL_SLIDER,
        "unit": "%",
        "step": 5,
    },
    US_CHAPTER_FONT_WEIGHT: {
        "type": US_TYPE_CHOICE,
        "choices": (0, 1, 2),
        "default": 1,
        "category": US_CATEGORY_READING,
        "label": "Font Weight",
        "control": US_CONTROL_BUTTONS,
        "options": [
            {"value": 0, "label": "Light"},
            {"value": 1, "label": "Normal"},
            {"value": 2, "label": "Bold"},
        ],
    },
    US_CHAPTER_PARAGRAPH_SPACING: {
        "type": US_TYPE_INT_RANGE,
        "min": 0,
        "max": 200,
        "default": 100,
        "category": US_CATEGORY_READING,
        "label": "Paragraph Spacing",
        "control": US_CONTROL_SLIDER,
        "unit": "%",
        "step": 5,
    },
    US_CHAPTER_CONTENT_PADDING: {
        "type": US_TYPE_INT_RANGE,
        "min": 3,
        "max": 20,
        "default": 3,
        "category": US_CATEGORY_READING,
        "label": "Margin",
        "control": US_CONTROL_SLIDER,
        "unit": "rem",
        "step": 1,
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
