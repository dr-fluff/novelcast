DEFAULT_SETTINGS = {
    "fanficfare": {
        "config_path": "config/fanficfare.ini",
        "defaults": {
            "output_format": "epub",
            "include_images": True,
            "is_adult": True,
            "language": "en",
            "timeout": 60,
            "retries": 3,
        },
    },
    "app": {
        "theme": "dark",
        "max_concurrent_jobs": 3,
        "default_sort": "title",
        "default_chapter_sort": "name",
        "font_size": "1em",
        "line_height": "1.5em",
        "time_format": "24h",
        "date_format": "%Y-%m-%d",
    },
    "downloads": {
        "path": "downloads",
    },
    "logging": {
        "level": "info",
        "file": "log/novelcast.log",
    },
    "library": {
        "data_path": "library/",
        "database_path": "library/library.db",
        "auto_update": True,
        "update_interval_hours": 24,
        "update_on_startup": True,
        "update_time": "02:00",
        "ignore_prefixes": "the,a,an",
    },
}