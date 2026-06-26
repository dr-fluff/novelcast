# novelcast/core/defaults.py

import string


SETTINGS = {
    "patreon": {
        "config_path": {
            "type": "string",
            "description": "Path to Patreon config file",
            "default": "config/patreon.ini",
            "label": "Config path",
        },
        "email": {
            "type": "string",
            "description": "Patreon email",
            "default": "email@email.com",
            "label": "Email",
        },
        "password": {
            "type": "secret",
            "description": "Patreon password",
            "default": "",
            "label": "Password",
        },
        "access_token": {
            "type": "secret",
            "description": "OAuth access token",
            "default": "",
            "label": "Access Token",
        },
        "refresh_token": {
            "type": "secret",
            "description": "OAuth refresh token",
            "default": "",
            "label": "Refresh Token",
        },
        "token_expiry": {
            "type": "string",
            "description": "Token expiry timestamp (ISO 8601)",
            "default": "",
            "label": "Token Expiry",
        },
        "creator_id": {
            "type": "string",
            "description": "Your Patreon creator ID",
            "default": "",
            "label": "Creator ID",
        },
    },
    
    "fanficfare": {
        "config_path": {
            "type": "string",
            "description": "Path to FanFicFare config file",
            "default": "config/fanficfare.ini",
            "label": "Config path",
        },

        # nested group → flattened for sanity
        "output_format": {
            "type": "select",
            "description": "Default output format for FanFicFare",
            "default": "epub",
            "options": ["epub", "mobi", "html", "txt"],
            "label": "Output format",
            "scope":"defaults",
        },
        "include_images": {
            "type": "bool",
            "description": "Whether to include images in the output",
            "default": True,
            "label": "Include images",
            "scope":"defaults",
        },
        "is_adult": {
            "type": "bool",
            "description": "Whether the content is adult",
            "default": True,
            "label": "Adult content",
            "scope":"defaults",
        },
        "language": {
            "type": "string",
            "description": "Default language for FanFicFare",
            "default": "en",
            "label": "Language",
            "scope":"defaults",
        },
        "timeout": {
            "type": "number",
            "description": "Request timeout for FanFicFare (seconds)",
            "default": 60,
            "min": 1,
            "max": 300,
            "label": "Timeout (seconds)",
            "scope":"defaults",
        },
        "retries": {
            "type": "number",
            "description": "Number of retries for failed requests in FanFicFare",
            "default": 3,
            "min": 0,
            "max": 10,
            "label": "Retries",
            "scope":"defaults",
        },
        "keep_summary_html": {
            "type": "bool",
            "description": "Whether to keep HTML in summaries",
            "default": True,
            "label": "Keep summary HTML",
            "scope":"epub",
        },
        "royalroad_email": {
            "type": "string",
            "description": "E-mail for RoyalRoad",
            "default": "email@email.com",
            "label": "E-mail",
            "scope": "www.royalroad.com",
            "ini_key": "e-mail",
        },
        "royalroad_password": {
            "type": "secret",
            "description": "Password for RoyalRoad",
            "default": "",
            "label": "Password",
            "scope": "www.royalroad.com",
            "ini_key": "password",
        },
        "royalroad_slow_down_sleep_time": {
            "type": "number",
            "description": "Sleep time between requests to RoyalRoad (seconds)",
            "default": 2,
            "min": 1,
            "max": 10,
            "label": "Slow down sleep time (seconds)",
            "scope": "www.royalroad.com",
        },
        "tthfanfic_username": {
            "type": "string",
            "description": "Username for TTHFanfic",
            "default": "Username",
            "label": "Username",
            "scope": "www.tthfanfic.org",
            "ini_key": "username",
        },
        "tthfanfic_email": {
            "type": "string",
            "description": "E-mail for TTHFanfic",
            "default": "email@email.com",
            "label": "E-mail",
            "scope": "www.tthfanfic.org",
            "ini_key": "e-mail",
            "legacy_key": "fanficfare.e-mail",
        },
        "tthfanfic_password": {
            "type": "secret",
            "description": "Password for TTHFanfic",
            "default": "",
            "label": "Password",
            "scope": "www.tthfanfic.org",
            "ini_key": "password",
            "legacy_key": "fanficfare.password",
        },
                
    },

    "app": {
        "theme": {
            "type": "select",
            "description": "Default theme for the application",
            "default": "dark",
            "options": ["light", "dark", "sepia"],
            "label": "Theme",
        },
        "max_concurrent_jobs": {
            "type": "number",
            "description": "Maximum number of concurrent download jobs",
            "default": 3,
            "min": 1,
            "max": 10,
            "label": "Max concurrent jobs",
        },
        "default_sort": {
            "type": "select",
            "description": "Default sort order for the library",
            "default": "title",
            "options": ["title", "author", "downloaded", "total_chapters", "last_updated", "created_at"],
            "label": "Default sort",
        },
        "default_chapter_sort": {
            "type": "select",
            "description": "Default sort order for chapters",
            "default": "name",
            "options": ["name", "number"],
            "label": "Chapter sort",
        },
        "font_size": {
            "type": "string",
            "description": "Default font size for the application",
            "default": "1em",
            "label": "Font size",
        },
        "line_height": {
            "type": "string",
            "description": "Default line height for the application",
            "default": "1.5em",
            "label": "Line height",
        },
        "time_format": {
            "type": "select",
            "description": "Default time format for the application",
            "default": "24h",
            "options": ["24h", "12h"],
            "label": "Time format",
        },
        "date_format": {
            "type": "string",
            "description": "Default date format for the application (strftime format)",
            "default": "%Y-%m-%d",
            "label": "Date format",
        },
    },

    "downloads": {
        "path": {
            "type": "string",
            "description": "Default download path for novels",
            "default": "downloads",
            "label": "Download path",
        },
    },

    "logging": {
        "level": {
            "type": "select",
            "description": "Log verbosity level",
            "default": "info",
            "options": ["debug", "info", "warning", "error"],
            "label": "Log level",
        },
        "file": {
            "type": "string",
            "description": "Log file path (relative to app root, leave empty for console only)",
            "default": "log/novelcast.log",
            "label": "Log file",
        },
        "max_bytes": {
            "type": "number",
            "description": "Maximum log file size before rotation (bytes)",
            "default": 10485760,   # 10 MB
            "min": 1048576,        # 1 MB
            "max": 104857600,      # 100 MB
            "label": "Max file size (bytes)",
        },
        "tail_buffer_size": {
            "type": "number",
            "description": "Number of recent log lines kept in memory for the live log viewer",
            "default": 500,
            "min": 50,
            "max": 5000,
            "label": "Live tail buffer (lines)",
        },
        "noisy_loggers": {
            "type": "string",
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
        "max_amount_of_files": {
            "type": "int",
            "description": "How many log files are going to be saved",
            "default": 20,
            "label": "Amount of saved log files",
        },
    },
    
    "library": {
        "data_path": {
            "type": "string",
            "description": "Path to the library data directory",
            "default": "data/",
            "label": "Data path",
        },
        "database_path": {
            "type": "string",
            "description": "Path to the library database file",
            "default": "data/novelcast.db",
            "label": "Database path",
        },
        "auto_update": {
            "type": "bool",
            "description": "Automatically check books in the library for new chapters",
            "default": True,
            "label": "Automatic sync",
        },
        "update_interval_hours": {
            "type": "number",
            "description": "How often automatic checks for new chapters run",
            "default": 24,
            "min": 1,
            "max": 168,
            "label": "Sync frequency (hours)",
        },
        "update_on_startup": {
            "type": "bool",
            "description": "Run an automatic check when NovelCast starts",
            "default": False,
            "label": "Sync on startup",
        },
        "update_time": {
            "type": "string",
            "description": "Time of day to check for updates (HH:MM, 24h format)",
            "default": "02:00",
            "label": "Update time",
        },
        "ignore_prefixes": {
            "type": "string",
            "description": "Comma-separated list of prefixes to ignore when sorting novels (e.g. 'the,a,an')",
            "default": "the,a,an",
            "label": "Ignore prefixes",
        },
    },
    
    "telegram": {
        "enabled": {
            "type": "bool",
            "description": "Enable Telegram bot integration",
            "default": False,
            "label": "Enable Telegram",
        },
        "bot_token": {
            "type": "secret",
            "description": "Telegram Bot API token (from @BotFather)",
            "default": "",
            "label": "Bot Token",
        },
        "chat_id": {
            "type": "string",
            "description": "Telegram chat ID to send messages to",
            "default": "",
            "label": "Chat ID",
        },
    },
}


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
}
