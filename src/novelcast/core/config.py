# novelcast/core/config.py

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ─────────────────────────────
    # ENVIRONMENT
    # ─────────────────────────────
    env: str = "development"

    # Debug auto-derived unless explicitly overridden
    debug: bool | None = None

    # ─────────────────────────────
    # SERVER
    # ─────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # ─────────────────────────────
    # DATABASE
    # ─────────────────────────────
    database_url: str = "sqlite:///data/novelcast.db"

    # ─────────────────────────────
    # SECURITY
    # ─────────────────────────────
    secret_key: str = Field(default="dev-secret-key-change-me", min_length=16)
    access_token_expire_minutes: int = 60

    # ─────────────────────────────
    # LOGGING
    # ─────────────────────────────
    log_level: str = "info"
    log_file: str = "novelcast.log"

    # ─────────────────────────────
    # CORS
    # ─────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000"]

    # ─────────────────────────────
    # VALIDATORS
    # ─────────────────────────────

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v

    @field_validator("debug", mode="before")
    @classmethod
    def set_debug(cls, v, values):
        # Auto-set debug based on env if not provided
        if v is None:
            env = values.data.get("env", "development")
            return env != "production"
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        # Allow comma-separated env string
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
