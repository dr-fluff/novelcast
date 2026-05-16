from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


class BaseKeyValueConfigWriter:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self._last_hash = None
        self._last_path = None

    def section_key(self) -> str:
        """Override in subclass (e.g. 'fanficfare', 'patreon')"""
        raise NotImplementedError

    def header(self) -> str | None:
        """Optional INI-style header"""
        return "defaults"


    def _format_value(self, value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _compute_hash(self, lines: list[str]) -> str:
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

    def _get_settings(self) -> dict:
        resolved = self.settings_service.get_resolved_server_settings()
        return resolved.get(self.section_key(), {})

    # -------------------------
    # BUILD
    # -------------------------

    def build_lines(self) -> list[str]:
        settings = self._get_settings()

        lines = []

        header = self.header()
        if header:
            lines.append(f"[{header}]")
            lines.append("")

        for key, value in settings.items():
            if key == "config_path":
                continue

            lines.append(f"{key}:{self._format_value(value)}")

        lines.append("")
        return lines

    # -------------------------
    # WRITE
    # -------------------------

    def write_config(self, force: bool = False) -> str:
        settings = self._get_settings()

        path = settings.get("config_path")
        if not path:
            raise RuntimeError(f"{self.section_key()}.config_path not set")

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
        path_obj.write_text(content, encoding="utf-8")

        self._last_hash = new_hash
        self._last_path = str(path_obj)

        logger.info(
            f"{self.section_key()} config written",
            extra={"path": str(path_obj)},
        )

        return str(path_obj)
    
class FanFicFareConfigService(BaseKeyValueConfigWriter):
    def section_key(self) -> str:
        return "fanficfare"

    def header(self) -> str:
        return "defaults"
    

class PatreonConfigService(BaseKeyValueConfigWriter):
    def section_key(self) -> str:
        return "patreon"

    def header(self):
        return "defaults"

    def build_lines(self) -> list[str]:
        lines = super().build_lines()
        encrypted_password = self.settings_service.get_raw_server_setting("patreon.password", "")

        if not encrypted_password:
            return lines

        return [
            f"password:{encrypted_password}" if line.startswith("password:") else line
            for line in lines
        ]
