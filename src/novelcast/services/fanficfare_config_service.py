# novelcast/services/fanficfare_config_service.py

from configparser import ConfigParser
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


class FanFicFareConfigService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self._last_hash = None
        self._last_path = None

    # -------------------------
    # INTERNAL
    # -------------------------

    def _compute_hash(self, lines: list[str]) -> str:
        return hashlib.sha256("\n".join(lines).encode()).hexdigest()

    def _get_fanficfare_settings(self) -> dict:
        resolved = self.settings_service.get_resolved_server_settings()
        return resolved.get("fanficfare", {})

    def _format_value(self, value):
        """
        FanFicFare prefers:
            key:value

        NOT:
            key = value

        Also normalize booleans.
        """

        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value)

    # -------------------------
    # BUILD
    # -------------------------

    def build_lines(self) -> list[str]:
        settings = self._get_fanficfare_settings()

        lines = ["[defaults]", ""]

        for key, value in settings.items():
            if key == "config_path":
                continue

            formatted = self._format_value(value)

            # IMPORTANT:
            # FanFicFare expects colon syntax.
            lines.append(f"{key}:{formatted}")

        lines.append("")

        return lines

    # -------------------------
    # WRITE
    # -------------------------

    def write_config(self, force: bool = False) -> str:
        settings = self._get_fanficfare_settings()

        path = settings.get("config_path")

        if not path:
            raise RuntimeError("fanficfare.config_path not set")

        lines = self.build_lines()

        new_hash = self._compute_hash(lines)

        path_obj = Path(path)

        if (
            not force
            and self._last_hash == new_hash
            and self._last_path == str(path_obj)
        ):
            return str(path_obj)

        path_obj.parent.mkdir(parents=True, exist_ok=True)

        content = "\n".join(lines)

        with open(path_obj, "w", encoding="utf-8") as f:
            f.write(content)

        self._last_hash = new_hash
        self._last_path = str(path_obj)

        logger.info(
            "FanFicFare config written",
            extra={"path": str(path_obj)},
        )

        return str(path_obj)