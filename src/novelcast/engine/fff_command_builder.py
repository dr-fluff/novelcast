# novelcast/engine/fff_command_builder.py

class FanFicFareCommandBuilder:
    def __init__(self, settings: dict):
        self.settings = settings

    def build(self, url: str) -> list[str]:
        cmd = ["fanficfare", "--json-meta"]

        # FORMAT
        if fmt := self.settings.get("fanficfare.format"):
            cmd += ["--format", fmt]

        # CONFIG FILE
        if cfg := self.settings.get("fanficfare.config_file"):
            cmd += ["--config", cfg]

        # UPDATE MODE
        if self.settings.get("fanficfare.update_mode") == "update-epub":
            cmd.append("--update-epub")

        if self.settings.get("fanficfare.update_mode") == "update-epub-always":
            cmd.append("--update-epub-always")

        # COOKIES
        if cookie := self.settings.get("fanficfare.cookie_file"):
            cmd += ["--mozilla-cookies", cookie]

        # EXTRA FLAGS (power-user escape hatch)
        if extra := self.settings.get("fanficfare.extra_args"):
            cmd += extra.split()

        # URL LAST
        cmd.append(url)

        return cmd