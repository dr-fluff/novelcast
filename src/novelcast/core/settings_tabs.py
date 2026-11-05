# novelcast/core/settings_tabs.py
"""Settings-page tab layout.

By default the settings page shows one tab per schema section. This module
lets a section be split across several tabs *for display only*: field names
(``section.key``), schema ``scope`` and ``ini_key`` are untouched, so saving the
form and generating ``fanficfare.ini`` behave exactly as before.
"""

import re

# Every FlareSolverr / Anubis-shim proxy key in defaults.py starts with this.
FLARESOLVERR_KEY_PREFIX = "royalroad_flaresolverr_"
ROYALROAD_SCOPE = "www.royalroad.com"
TTHFANFIC_SCOPE = "www.tthfanfic.org"


def _is_proxy(key: str, meta: dict) -> bool:
    return key.startswith(FLARESOLVERR_KEY_PREFIX)


def _is_royalroad(key: str, meta: dict) -> bool:
    return meta.get("scope") == ROYALROAD_SCOPE and not _is_proxy(key, meta)


def _is_tthfanfic(key: str, meta: dict) -> bool:
    return meta.get("scope") == TTHFANFIC_SCOPE


def _matches(*keys: str):
    return lambda key, meta: key in keys


# section -> extra tabs carved out of it, as (tab_id, label, matcher), in display
# order. Anything that matches no matcher stays on the section's own tab.
TAB_SPLITS = {
    "app": [
        ("app_display", "Display", _matches("font_size", "line_height", "time_format", "date_format")),
        ("app_library_view", "Library view", _matches("default_sort", "default_chapter_sort")),
        ("app_downloads_general", "General", _matches("max_concurrent_jobs")),
    ],
    "library": [
        ("library_storage", "Storage", _matches("data_path", "database_path")),
        ("library_view", "Library view", _matches("ignore_prefixes")),
        (
            "library_updates",
            "Updates",
            _matches("auto_update", "update_interval_hours", "update_on_startup", "update_time"),
        ),
    ],
    "fanficfare": [
        ("fff_proxy", "Proxy", _is_proxy),
        ("royalroad", "RoyalRoad", _is_royalroad),
        ("fff_tthfanfic", "TTHFanfic", _is_tthfanfic),
    ],
    "scrapers": [
        ("scrapers_royalroad", "RoyalRoad", _matches("royalroad_enabled")),
        ("scrapers_scribblehub", "ScribbleHub", _matches("scribblehub_enabled")),
        ("scrapers_patreon", "Patreon", _matches("patreon_enabled")),
    ],
    "rss": [("rss_royalroad", "RoyalRoad", _matches("royalroad"))],
}
def _category_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return f"category-{slug}"


def build_settings_tabs(schema: dict, server_settings: dict, tab_layout: dict | None = None) -> list[dict]:
    """Return the tab list for the settings page.

    ``server_settings`` is the already-scoped structure the route builds:
    ``{section: {scope: {key: value}}}``. Each returned tab is
    ``{"id", "label", "section", "scoped"}`` where ``scoped`` has the same
    ``{scope: {key: value}}`` shape the template already iterates. (Not named
    ``values``: Jinja's ``tab.values`` would resolve to ``dict.values``.) Every schema
    section gets a tab, in schema order, with its split-off tabs right after it.
    """
    tabs: list[dict] = []
    tab_layout = tab_layout or {}

    for section, fields in schema.items():
        values = server_settings.get(section, {})
        splits = TAB_SPLITS.get(section, [])

        remainder: dict = {}
        buckets: dict[str, dict] = {tab_id: {} for tab_id, _, _ in splits}

        for scope, scope_fields in values.items():
            for key, value in scope_fields.items():
                meta = fields.get(key) or {}
                target = remainder
                for tab_id, _, matches in splits:
                    if matches(key, meta):
                        target = buckets[tab_id]
                        break
                target.setdefault(scope, {})[key] = value

        if remainder or not splits:
            tabs.append({"id": section, "section": section, "scoped": remainder})
        for tab_id, label, _ in splits:
            if buckets[tab_id]:
                tabs.append({"id": tab_id, "label": label, "section": section, "scoped": buckets[tab_id]})

    for tab in tabs:
        layout = tab_layout.get(tab["id"], {})
        fallback_label = tab.get("label", tab["section"].capitalize())
        tab["category"] = layout.get("category", fallback_label)
        tab["subcategory"] = layout.get("subcategory")
        tab["label"] = tab["subcategory"] or layout.get("label") or fallback_label
        tab["category_id"] = _category_id(tab["category"])

    schema_order = {tab["id"]: index for index, tab in enumerate(tabs)}
    layout_order = {tab_id: index for index, tab_id in enumerate(tab_layout)}
    tabs.sort(key=lambda tab: layout_order.get(tab["id"], len(layout_order) + schema_order[tab["id"]]))

    return tabs


def build_settings_tab_categories(tabs: list[dict], tab_layout: dict | None = None) -> list[dict]:
    """Group tabs by configured category and mark multi-tab groups."""
    categories: list[dict] = []
    categories_by_id: dict[str, dict] = {}
    tab_layout = tab_layout or {}
    schema_order = {tab["id"]: index for index, tab in enumerate(tabs)}
    layout_order = {tab_id: index for index, tab_id in enumerate(tab_layout)}

    for tab in tabs:
        category_id = tab["category_id"]
        category = categories_by_id.get(category_id)
        if category is None:
            category = {"id": category_id, "label": tab["category"], "tabs": []}
            categories_by_id[category_id] = category
            categories.append(category)
        category["tabs"].append(tab)

    for category in categories:
        category["tabs"].sort(
            key=lambda tab: layout_order.get(
                tab["id"], len(layout_order) + schema_order[tab["id"]]
            )
        )
        category["grouped"] = len(category["tabs"]) > 1 or any(tab["subcategory"] for tab in category["tabs"])
        subcategories_by_label: dict[str, dict] = {}
        grouped_tabs = []
        for tab in category["tabs"]:
            tab["category_grouped"] = category["grouped"]
            if category["grouped"]:
                subcategory_label = tab["subcategory"] or tab["label"]
                tab["subcategory_label"] = subcategory_label
                subcategory = subcategories_by_label.get(subcategory_label)
                if subcategory is None:
                    subcategory = {"label": subcategory_label, "tabs": []}
                    subcategories_by_label[subcategory_label] = subcategory
                    grouped_tabs.append(subcategory)
                subcategory["tabs"].append(tab)

        for group in grouped_tabs:
            group_tabs = group["tabs"]
            for index, tab in enumerate(group_tabs):
                tab["subcategory_group_start"] = index == 0
                tab["subcategory_group_end"] = index == len(group_tabs) - 1
        category["subcategories"] = grouped_tabs

    return categories