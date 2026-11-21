import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", validation_alias="GEMINI_MODEL")
    max_sessions: int = Field(default=100, validation_alias="MAX_SESSIONS")

    # Deployment settings
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    env: str = Field(default="development", validation_alias="ENV")

    # Security, Auth & CORS
    app_api_key: str = Field(default="", validation_alias="APP_API_KEY")
    api_auth_token: str = Field(default="", validation_alias="API_AUTH_TOKEN")
    allowed_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="ALLOWED_ORIGINS",
    )
    rate_limit_per_min: int = Field(default=30, validation_alias="RATE_LIMIT_PER_MIN")
    rate_limit_per_minute: int = Field(default=30, validation_alias="RATE_LIMIT_PER_MINUTE")
    max_message_chars: int = Field(default=4000, validation_alias="MAX_MESSAGE_CHARS")

    # Database
    memory_db_path: str = Field(default="", validation_alias="MEMORY_DB_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_keys(self) -> List[str]:
        """Returns parsed list of valid API keys from APP_API_KEY or legacy API_AUTH_TOKEN."""
        raw = (self.app_api_key or self.api_auth_token).strip()
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def effective_rate_limit(self) -> int:
        """Returns configured requests per minute limit."""
        return self.rate_limit_per_min or self.rate_limit_per_minute or 30


settings = Settings()
