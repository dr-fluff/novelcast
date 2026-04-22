from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )
    
    env: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    database_url: str = "sqlite:///data/novelcast.db"

    secret_key: str = Field(..., min_length=32)
    access_token_expire_minutes: int = 60

    log_level: str = "info"
    log_file: str = "novelcast.log"

    cors_origins: str = "http://localhost:3000"

    @field_validator("port")
    @classmethod
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v