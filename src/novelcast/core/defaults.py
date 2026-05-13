# novelcast/core/defaults.py

SETTINGS = {
    "fanficfare": {
        "config_path": {
            "type": "string",
            "default": "config/fanficfare.ini",
            "label": "Config path",
        },

        # nested group → flattened for sanity
        "output_format": {
            "type": "select",
            "default": "epub",
            "options": ["epub", "mobi", "html", "txt"],
            "label": "Output format",
        },
        "include_images": {
            "type": "bool",
            "default": True,
            "label": "Include images",
        },
        "is_adult": {
            "type": "bool",
            "default": True,
            "label": "Adult content",
        },
        "language": {
            "type": "string",
            "default": "en",
            "label": "Language",
        },
        "timeout": {
            "type": "number",
            "default": 60,
            "min": 1,
            "max": 300,
            "label": "Timeout (seconds)",
        },
        "retries": {
            "type": "number",
            "default": 3,
            "min": 0,
            "max": 10,
            "label": "Retries",
        },
    },

    "app": {
        "theme": {
            "type": "select",
            "default": "dark",
            "options": ["light", "dark", "sepia"],
            "label": "Theme",
        },
        "max_concurrent_jobs": {
            "type": "number",
            "default": 3,
            "min": 1,
            "max": 10,
            "label": "Max concurrent jobs",
        },
        "default_sort": {
            "type": "select",
            "default": "title",
            "options": ["title", "author", "downloaded"],
            "label": "Default sort",
        },
        "default_chapter_sort": {
            "type": "select",
            "default": "name",
            "options": ["name", "number"],
            "label": "Chapter sort",
        },
        "font_size": {
            "type": "string",
            "default": "1em",
            "label": "Font size",
        },
        "line_height": {
            "type": "string",
            "default": "1.5em",
            "label": "Line height",
        },
        "time_format": {
            "type": "select",
            "default": "24h",
            "options": ["24h", "12h"],
            "label": "Time format",
        },
        "date_format": {
            "type": "string",
            "default": "%Y-%m-%d",
            "label": "Date format",
        },
    },

    "downloads": {
        "path": {
            "type": "string",
            "default": "downloads",
            "label": "Download path",
        },
    },

    "logging": {
        "level": {
            "type": "select",
            "default": "info",
            "options": ["debug", "info", "warning", "error"],
            "label": "Log level",
        },
        "file": {
            "type": "string",
            "default": "log/novelcast.log",
            "label": "Log file",
        },
    },

    "library": {
        "data_path": {
            "type": "string",
            "default": "data/",
            "label": "Data path",
        },
        "database_path": {
            "type": "string",
            "default": "data/novelcast.db",
            "label": "Database path",
        },
        "auto_update": {
            "type": "bool",
            "default": True,
            "label": "Auto update",
        },
        "update_interval_hours": {
            "type": "number",
            "default": 24,
            "min": 1,
            "max": 168,
            "label": "Update interval (hours)",
        },
        "update_on_startup": {
            "type": "bool",
            "default": True,
            "label": "Update on startup",
        },
        "update_time": {
            "type": "string",
            "default": "02:00",
            "label": "Update time",
        },
        "ignore_prefixes": {
            "type": "string",
            "default": "the,a,an",
            "label": "Ignore prefixes",
        },
    },
}

