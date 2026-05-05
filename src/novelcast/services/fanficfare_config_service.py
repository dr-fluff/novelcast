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
    def _compute_hash(self, config: ConfigParser) -> str:
        items = []

        for section in config.sections():
            for key, value in sorted(config[section].items()):
                items.append(f"{section}.{key}={value}")

        return hashlib.sha256("\n".join(items).encode()).hexdigest()

    def _get_fanficfare_settings(self) -> dict:
        resolved = self.settings_service.get_resolved_server_settings()
        return resolved.get("fanficfare", {})

    # -------------------------
    # BUILD
    # -------------------------
    def build_config(self) -> ConfigParser:
        settings = self._get_fanficfare_settings()

        config = ConfigParser()
        section = "defaults"

        config[section] = {}

        for key, value in settings.items():
            if key == "config_path":
                continue
            config[section][key] = str(value)

        return config

    # -------------------------
    # WRITE
    # -------------------------
    def write_config(self, force: bool = False) -> str:
        settings = self._get_fanficfare_settings()

        path = settings.get("config_path")
        if not path:
            raise RuntimeError("fanficfare.config_path not set")

        config = self.build_config()
        new_hash = self._compute_hash(config)

        path_obj = Path(path)

        if not force and self._last_hash == new_hash and self._last_path == str(path_obj):
            return str(path_obj)

        path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(path_obj, "w", encoding="utf-8") as f:
            config.write(f)

        self._last_hash = new_hash
        self._last_path = str(path_obj)

        logger.info("FanFicFare config written", extra={"path": str(path_obj)})

        return str(path_obj)