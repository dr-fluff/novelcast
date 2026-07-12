# novelcast/services/site_adapters/registry.py

from typing import Optional

from novelcast.core import setting_keys
from novelcast.core.defaults import SETTINGS

from .base import SiteAdapter
from .royalroad import RoyalRoadAdapter
from .scribblehub import ScribbleHubAdapter
from .patreon import PatreonAdapter


_ADAPTERS: dict[str, SiteAdapter] = {
    "royalroad": RoyalRoadAdapter(),
    "scribblehub": ScribbleHubAdapter(),
    "patreon": PatreonAdapter(),
}


ALIAS_MAP = {
    "rr": "royalroad",
    "royalroad": "royalroad",
    "sh": "scribblehub",
    "scribblehub": "scribblehub",
}

_ENABLED_SETTING = {
    "patreon":     setting_keys.SCRAPERS_SETTINGS.PATREON_ENABLED,
    "royalroad":   setting_keys.SCRAPERS_SETTINGS.ROYALROAD_ENABLED,
    "scribblehub": setting_keys.SCRAPERS_SETTINGS.SCRIBBLEHUB_ENABLED,
}


def all_sites() -> list[str]:
    return list(_ADAPTERS.keys())


def get_adapter(site: str) -> Optional[SiteAdapter]:
    return _ADAPTERS.get(site)


def resolve_alias(token: str) -> Optional[str]:
    return ALIAS_MAP.get(token.lower())


def _schema_default(dotted_key: str) -> bool:
    """Fallback used when no settings_service is available — reads the
    schema's own declared default instead of blindly assuming True."""
    section, _, key = dotted_key.partition(".")
    return bool(SETTINGS.get(section, {}).get(key, {}).get("default", True))


def is_enabled(site: str, settings_service=None) -> bool:
    """Whether `site` (including 'patreon') is currently enabled,
    per the SETTINGS schema in defaults.py.
    """
    dotted_key = _ENABLED_SETTING.get(site)
    if dotted_key is None:
        return True

    if settings_service is None:
        # Not wired at this call site — fall back to schema default
        # rather than assuming enabled (Patreon defaults to False).
        return _schema_default(dotted_key)

    return bool(settings_service.get(dotted_key, default=_schema_default(dotted_key)).value)


def enabled_sites(settings_service=None) -> list[str]:
    return [s for s in all_sites() if is_enabled(s, settings_service)]