# novelcast/core/setting_keys.py

from types import SimpleNamespace

from novelcast.core.defaults import SETTINGS


class _SectionKeys(SimpleNamespace):
    def __repr__(self) -> str:
        keys = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"<SectionKeys {keys}>"


def _build_section(section: str, fields: dict) -> _SectionKeys:
    attrs = {key.upper(): f"{section}.{key}" for key, meta in fields.items() if isinstance(meta, dict)}
    return _SectionKeys(**attrs)


def _build_all() -> dict:
    return {f"{section.upper()}_SETTINGS": _build_section(section, fields) for section, fields in SETTINGS.items()}


_generated = _build_all()
globals().update(_generated)

__all__ = list(_generated.keys())
