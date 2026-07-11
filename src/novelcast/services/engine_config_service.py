# novelcast/services/engine_config_service.py

import hashlib
import logging
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────
# INI BUILDER (NO STRING LOGIC OUTSIDE HERE)
# ─────────────────────────────


class IniBuilder:
    def __init__(self):
        self.sections: dict[str, OrderedDict[str, str]] = {}

    def add(self, section: str, key: str, value: str):
        if section not in self.sections:
            self.sections[section] = OrderedDict()
        self.sections[section][key] = value

    def render(self, section_order: list[str] | None = None) -> list[str]:
        lines = []

        if section_order:
            ordered_sections = sorted(
                self.sections.items(),
                key=lambda x: section_order.index(x[0]) if x[0] in section_order else 999,
            )
        else:
            ordered_sections = self.sections.items()

        for section, values in ordered_sections:
            lines.append(f"[{section}]")
            lines.append("")

            for k, v in values.items():
                lines.append(f"{k}:{v}")

            lines.append("")

        return lines


# ─────────────────────────────
# BASE ENGINE CONFIG SERVICE
# ─────────────────────────────


class BaseEngineConfigService:
    """
    Shared engine config writer.

    Responsibilities:
    - fetch settings
    - group by scope
    - delegate formatting
    - delegate engine-specific hooks
    """

    SECTION_ORDER = ["defaults"]

    def __init__(self, settings_service):
        self.settings_service = settings_service
        self._last_hash = None
        self._last_path = None

    # -------------------------
    # OVERRIDES
    # -------------------------

    def section_key(self) -> str:
        raise NotImplementedError

    def section_order(self) -> list[str]:
        return self.SECTION_ORDER

    def header(self) -> str | None:
        return None  # INI header not required anymore

    # -------------------------
    # FORMATTING
    # -------------------------

    def _format_value(self, key: str, value) -> str:
        # meta = self.settings_service.get_field_meta(self.section_key(), key)

        # # if meta.get("type") == "secret":
        # #     return "${SECRET}"

        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value)

    # -------------------------
    # SETTINGS
    # -------------------------

    def _get_settings(self) -> dict:
        resolved = self.settings_service.get_resolved_server_settings()
        return resolved.get(self.section_key(), {})

    def _get_meta(self, key: str) -> dict:
        return self.settings_service.get_field_meta(self.section_key(), key)

    # -------------------------
    # BUILD INI
    # -------------------------

    def build_builder(self) -> IniBuilder:
        settings = self._get_settings()
        builder = IniBuilder()

        for key, value in settings.items():
            if key == "config_path":
                continue

            meta = self._get_meta(key)
            scope = meta.get("scope", "defaults")

            formatted_value = self._format_value(key, value)

            # hook for engine-specific mutation
            formatted_value = self.post_format(key, formatted_value)

            builder.add(scope, meta.get("ini_key", key), formatted_value)

        return self.post_build(builder)

    # hook: per-value override
    def post_format(self, key: str, value: str) -> str:
        return value

    # hook: whole-document override
    def post_build(self, builder: IniBuilder) -> IniBuilder:
        return builder

    # -------------------------
    # RENDER
    # -------------------------

    def build_lines(self) -> list[str]:
        builder = self.build_builder()

        return builder.render(section_order=self.section_order())

    # -------------------------
    # WRITE
    # -------------------------

    def _compute_hash(self, lines: list[str]) -> str:
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

    def write_config(self, force: bool = False) -> str:
        settings = self._get_settings()

        path = settings.get("config_path")
        if not path:
            raise RuntimeError(f"{self.section_key()}.config_path not set")

        lines = self.build_lines()
        new_hash = self._compute_hash(lines)

        path_obj = Path(path)

        if not force and self._last_hash == new_hash and self._last_path == str(path_obj):
            return str(path_obj)

        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text("\n".join(lines), encoding="utf-8")

        self._last_hash = new_hash
        self._last_path = str(path_obj)

        logger.info(
            f"{self.section_key()} config written",
            extra={"path": str(path_obj)},
        )

        return str(path_obj)


class FanFicFareConfigService(BaseEngineConfigService):
    SECTION_ORDER = ["defaults", "epub"]

    def section_key(self) -> str:
        return "fanficfare"

    def section_order(self) -> list[str]:
        order = list(self.SECTION_ORDER)
        schema = self.settings_service.schema.get(self.section_key(), {})

        for meta in schema.values():
            scope = meta.get("scope", "defaults")
            if scope not in order:
                order.append(scope)

        for domain in self.settings_service.get_site_overrides():
            if domain not in order:
                order.append(domain)

        return order

    def post_build(self, builder: IniBuilder) -> IniBuilder:
        for domain, fields in self.settings_service.get_site_overrides().items():
            for key, value in fields.items():
                builder.add(domain, key, self._format_value(key, value))

        return builder
