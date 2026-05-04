# novelcast/services/fanficfare_config_service.py

from configparser import ConfigParser
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FanFicFareConfigService:
    def __init__(self, settings_repo):
        self.settings_repo = settings_repo

    def build_config(self) -> ConfigParser:
        settings = self.settings_repo.get_all_server_settings()

        config = ConfigParser()

        for key, value in settings.items():
            if not key.startswith("fanficfare."):
                continue

            # fanficfare.defaults.output_format
            parts = key.split(".")

            if len(parts) < 3:
                continue

            _, section, option = parts[0], parts[1], ".".join(parts[2:])

            if section not in config:
                config[section] = {}

            config[section][option] = str(value)

        return config

    def write_config(self) -> str:
        settings = self.settings_repo.get_all_server_settings()
        path = settings.get("fanficfare.config_path")

        if not path:
            raise RuntimeError("fanficfare.config_path not set")

        config = self.build_config()

        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(path_obj, "w", encoding="utf-8") as f:
            config.write(f)

        logger.info("FanFicFare config written", extra={"path": path})

        return str(path_obj)