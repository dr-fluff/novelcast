from typing import Optional

from novelcast.core.defaults import SETTINGS
from .base import SiteAdapter
from .royalroad import RoyalRoadAdapter
from .scribblehub import ScribbleHubAdapter

_ADAPTERS: dict[str, SiteAdapter] = {
    "royalroad": RoyalRoadAdapter(),
    "scribblehub": ScribbleHubAdapter(),
}

ALIAS_MAP = {
    "rr": "royalroad",
    "royalroad": "royalroad",
    "sh": "scribblehub",
    "scribblehub": "scribblehub",
}

_ENABLED_SETTING = {
    "patreon":     ("patreon", "enabled"),
    "royalroad":   ("scrapers", "royalroad_enabled"),
    "scribblehub": ("scrapers", "scribblehub_enabled"),
}


def all_sites() -> list[str]:
    return list(_ADAPTERS.keys())


def get_adapter(site: str) -> Optional[SiteAdapter]:
    return _ADAPTERS.get(site)


def resolve_alias(token: str) -> Optional[str]:
    return ALIAS_MAP.get(token.lower())


def _schema_default(section: str, key: str) -> bool:
    """Fallback used when no settings_service is available — reads the
    schema's own declared default instead of blindly assuming True."""
    return bool(SETTINGS.get(section, {}).get(key, {}).get("default", True))


def is_enabled(site: str, settings_service=None) -> bool:
    """Whether `site` (including 'patreon') is currently enabled,
    per the SETTINGS schema in defaults.py.
    """
    mapping = _ENABLED_SETTING.get(site)
    if mapping is None:
        return True

    section, key = mapping

    if settings_service is None:
        # Not wired at this call site — fall back to schema default
        # rather than assuming enabled (Patreon defaults to False).
        return _schema_default(section, key)

    resolved = settings_service.get_resolved_server_settings()
    return bool(resolved.get(section, {}).get(key, _schema_default(section, key)))


def enabled_sites(settings_service=None) -> list[str]:
    return [s for s in all_sites() if is_enabled(s, settings_service)]