from novelcast.core.defaults import FANFICTIONFARE_DEFAULTS, FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME, SETTINGS_TAB_LAYOUT
from novelcast.core.settings_tabs import build_settings_tab_categories, build_settings_tabs


def test_royalroad_request_delay_can_be_disabled():
    setting = FANFICTIONFARE_DEFAULTS[FFF_ROYALROAD_SLOW_DOWN_SLEEP_TIME]

    assert setting["default"] == 0
    assert setting["min"] == 0


def test_settings_are_grouped_by_category_and_subcategory_without_changing_ownership():
    schema = {
        "app": {
            "font_size": {},
            "line_height": {},
            "time_format": {},
            "date_format": {},
            "default_sort": {},
            "default_chapter_sort": {},
            "max_concurrent_jobs": {},
        },
        "library": {
            "data_path": {},
            "database_path": {},
            "auto_update": {},
            "update_interval_hours": {},
            "update_on_startup": {},
            "update_time": {},
            "ignore_prefixes": {},
        },
        "fanficfare": {
            "config_path": {},
            "royalroad_email": {"scope": "www.royalroad.com"},
            "royalroad_password": {"scope": "www.royalroad.com"},
            "royalroad_slow_down_sleep_time": {"scope": "www.royalroad.com"},
            "royalroad_flaresolverr_proxy": {},
            "tthfanfic_username": {"scope": "www.tthfanfic.org"},
        },
        "scrapers": {"royalroad_enabled": {}, "scribblehub_enabled": {}, "patreon_enabled": {}},
        "rss": {"enabled": {}, "interval": {}, "royalroad": {}},
        "downloads": {"path": {}},
        "patreon": {"enabled": {}, "session_cookie": {}},
        "telegram": {"enabled": {}},
        "logging": {"level": {}},
    }
    server_settings = {
        "app": {
            "user": {
                "font_size": "1em",
                "line_height": "1.5em",
                "time_format": "24h",
                "date_format": "%Y-%m-%d",
                "default_sort": "title",
                "default_chapter_sort": "name",
                "max_concurrent_jobs": 3,
            }
        },
        "library": {
            "server": {
                "data_path": "data/",
                "database_path": "data/novelcast.db",
                "auto_update": True,
                "update_interval_hours": 24,
                "update_on_startup": False,
                "update_time": "02:00",
                "ignore_prefixes": "the,a,an",
            }
        },
        "fanficfare": {
            "server": {
                "config_path": "config/fanficfare.ini",
                "royalroad_email": "reader@example.com",
                "royalroad_password": "secret",
                "royalroad_slow_down_sleep_time": 2,
                "royalroad_flaresolverr_proxy": "http://localhost:8191",
                "tthfanfic_username": "reader",
            }
        },
        "scrapers": {"server": {"royalroad_enabled": True, "scribblehub_enabled": False, "patreon_enabled": False}},
        "rss": {"server": {"enabled": True, "interval": 10, "royalroad": True}},
        "downloads": {"server": {"path": "/novels"}},
        "patreon": {"server": {"enabled": False, "session_cookie": "cookie"}},
        "telegram": {"server": {"enabled": False}},
        "logging": {"server": {"level": "info"}},
    }

    tabs = build_settings_tabs(schema, server_settings, SETTINGS_TAB_LAYOUT)
    categories = build_settings_tab_categories(tabs, SETTINGS_TAB_LAYOUT)

    assert [category["label"] for category in categories] == [
        "Appearance",
        "Library",
        "Downloads",
        "Sources",
        "Notifications",
        "System",
    ]
    appearance = categories[0]
    assert [group["label"] for group in appearance["subcategories"]] == ["Display", "Library view"]
    library = categories[1]
    updates = next(group for group in library["subcategories"] if group["label"] == "Updates")
    assert [tab["id"] for tab in updates["tabs"]] == ["library_updates", "rss"]
    downloads = categories[2]
    general = next(group for group in downloads["subcategories"] if group["label"] == "General")
    assert [tab["id"] for tab in general["tabs"]] == ["app_downloads_general", "downloads"]
    proxy = next(group for group in downloads["subcategories"] if group["label"] == "Proxy")
    assert proxy["tabs"][0]["scoped"]["server"]["royalroad_flaresolverr_proxy"] == "http://localhost:8191"
    sources = categories[3]
    royalroad = next(group for group in sources["subcategories"] if group["label"] == "RoyalRoad")
    assert [tab["id"] for tab in royalroad["tabs"]] == [
        "scrapers_royalroad",
        "rss_royalroad",
        "royalroad",
    ]
    assert next(tab for tab in royalroad["tabs"] if tab["id"] == "royalroad")["scoped"]["server"] == {
        "royalroad_email": "reader@example.com",
        "royalroad_password": "secret",
        "royalroad_slow_down_sleep_time": 2,
    }


def test_settings_category_layout_can_add_an_app_subcategory():
    schema = {"app": {"theme": {}}, "app_advanced": {"setting": {}}}
    server_settings = {
        "app": {"user": {"theme": "dark"}},
        "app_advanced": {"server": {"setting": True}},
    }
    layout = {
        "app": {"category": "App", "subcategory": "General"},
        "app_advanced": {"category": "App", "subcategory": "Advanced"},
    }

    tabs = build_settings_tabs(schema, server_settings, layout)
    categories = build_settings_tab_categories(tabs, layout)

    app_category = categories[0]
    assert app_category["label"] == "App"
    assert app_category["grouped"] is True
    assert [tab["subcategory_label"] for tab in app_category["tabs"]] == ["General", "Advanced"]
    assert [category["label"] for category in categories] == ["App"]


def test_telegram_is_a_webhook_notifications_subcategory():
    schema = {"telegram": {"enabled": {}}}
    server_settings = {"telegram": {"server": {"enabled": True}}}

    tabs = build_settings_tabs(schema, server_settings, SETTINGS_TAB_LAYOUT)
    categories = build_settings_tab_categories(tabs, SETTINGS_TAB_LAYOUT)

    assert categories[0]["label"] == "Notifications"
    assert categories[0]["grouped"] is True
    assert categories[0]["tabs"][0]["subcategory_label"] == "Telegram"