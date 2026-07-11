"""
novelcast/services/logging_service.py

Drop this in novelcast/services/ and add it to novelcast/services/__init__.py:
    from .logging_service import LoggingService
"""

from __future__ import annotations

import logging

from novelcast.core.logging import LogConfig, setup_logging

logger = logging.getLogger(__name__)


class LoggingService:
    """
    Bridges SettingsService ↔ setup_logging().
    Injected into AppContext; call .apply() at startup and after admin saves.
    """

    def __init__(self, settings_service) -> None:
        self._settings = settings_service

    def apply(self) -> LogConfig:
        try:
            cfg = LogConfig.from_settings_service(self._settings)
        except Exception as exc:
            cfg = LogConfig()
            print(f"[LoggingService] DB not ready, using defaults: {exc}")

        setup_logging(cfg)

        logger.info(
            "Logging reconfigured",
            extra={
                "extra_data": {
                    "level": cfg.level,
                    "file": cfg.file_path or "(console only)",
                    "max_bytes": cfg.max_bytes,
                    "buf_size": cfg.tail_buffer_size,
                    "max_amount_of_files": cfg.max_files,
                }
            },
        )
        return cfg

    def current_config(self) -> LogConfig:
        """Return config as it sits in DB without applying it."""
        return LogConfig.from_settings_service(self._settings)
