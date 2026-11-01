# novelcast/core/settings_tabs.py
"""Settings-page tab layout.

By default the settings page shows one tab per schema section. This module
lets a section be split across several tabs *for display only*: field names
(``section.key``), schema ``scope`` and ``ini_key`` are untouched, so saving the
form and generating ``fanficfare.ini`` behave exactly as before.
"""

# Every FlareSolverr / Anubis-shim proxy key in defaults.py starts with this.
FLARESOLVERR_KEY_PREFIX = "royalroad_flaresolverr_"
ROYALROAD_SCOPE = "www.royalroad.com"


def _is_anubis(key: str, meta: dict) -> bool:
    return key.startswith(FLARESOLVERR_KEY_PREFIX)


def _is_royalroad(key: str, meta: dict) -> bool:
    return meta.get("scope") == ROYALROAD_SCOPE and not _is_anubis(key, meta)


# section -> extra tabs carved out of it, as (tab_id, label, matcher), in display
# order. Anything that matches no matcher stays on the section's own tab.
TAB_SPLITS = {
    "fanficfare": [
        ("royalroad", "RoyalRoad", _is_royalroad),
        ("anubis", "Anubis", _is_anubis),
    ],
}

# Display labels for section tabs that shouldn't just be section.capitalize().
TAB_LABELS = {
    "fanficfare": "FanFicFare",
}


def build_settings_tabs(schema: dict, server_settings: dict) -> list[dict]:
    """Return the tab list for the settings page.

    ``server_settings`` is the already-scoped structure the route builds:
    ``{section: {scope: {key: value}}}``. Each returned tab is
    ``{"id", "label", "section", "scoped"}`` where ``scoped`` has the same
    ``{scope: {key: value}}`` shape the template already iterates. (Not named
    ``values``: Jinja's ``tab.values`` would resolve to ``dict.values``.) Every schema
    section gets a tab, in schema order, with its split-off tabs right after it.
    """
    tabs: list[dict] = []

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

        tabs.append(
            {
                "id": section,
                "label": TAB_LABELS.get(section, section.capitalize()),
                "section": section,
                "scoped": remainder,
            }
        )
        for tab_id, label, _ in splits:
            tabs.append(
                {
                    "id": tab_id,
                    "label": label,
                    "section": section,
                    "scoped": buckets[tab_id],
                }
            )

    return tabs