# novelcast/engine/fanficfare_engine.py

import subprocess
import json
import logging

from curses import raw
from unittest import result

from novelcast.engine.fff_command_builder import FanFicFareCommandBuilder
from .base import StoryEngine

logger = logging.getLogger(__name__)

class FanFicFareEngine(StoryEngine):
    def __init__(self, settings_repo, config_service):
        self.settings_repo = settings_repo
        self.config_service = config_service

    def can_handle(self, url: str) -> bool:
        return True
    
    def fetch(self, url: str) -> dict:
        config_path = self.config_service.write_config()

        cmd = [
            "fanficfare",
            "--json-meta",
            "--non-interactive",
            "--config", config_path,
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        
        logger.error("FFF STDOUT: %s", result.stdout)
        logger.error("FFF STDERR: %s", result.stderr)

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        raw = json.loads(result.stdout)
        epub_path = self._extract_epub_path(raw)

        return {
            "file_path": epub_path,
            "title": raw.get("title"),
            "author": raw.get("author"),
            "url": url
        }
        
    
    def _extract_epub_path(self, raw: dict) -> str:
        possible_keys = [
            "output_filename",
            "outfile",
            "filename",
        ]

        for key in possible_keys:
            if key in raw and raw[key]:
                return raw[key]

        raise RuntimeError(f"Could not find EPUB path in response: {raw.keys()}")
    
    