import logging
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_fake: bool = Field(default=False, validation_alias="GEMINI_FAKE")
    max_sessions: int = Field(default=100, validation_alias="MAX_SESSIONS")

    # Deployment settings
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    env: str = Field(default="development", validation_alias="ENV")

    # Security, Auth & CORS
    app_api_key: str = Field(default="", validation_alias="APP_API_KEY")
    app_admin_keys: str = Field(default="", validation_alias="APP_ADMIN_KEYS")
    api_auth_token: str = Field(default="", validation_alias="API_AUTH_TOKEN")
    allowed_origins: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="ALLOWED_ORIGINS",
    )
    rate_limit_per_min: int = Field(
        default=30,
        validation_alias=AliasChoices("RATE_LIMIT_PER_MIN", "RATE_LIMIT_PER_MINUTE"),
    )
    rate_limit_heavy_per_min: int = Field(
        default=5,
        validation_alias=AliasChoices("RATE_LIMIT_HEAVY_PER_MIN"),
    )
    max_message_chars: int = Field(default=4000, validation_alias="MAX_MESSAGE_CHARS")

    # Database
    memory_db_path: str = Field(default="data/memory.db", validation_alias="MEMORY_DB_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def api_keys(self) -> List[str]:
        """Returns parsed list of valid API keys from APP_API_KEY or legacy API_AUTH_TOKEN."""
        if self.api_auth_token and not self.app_api_key:
            logger.warning(
                "DEPRECATION WARNING: 'API_AUTH_TOKEN' is deprecated and will be removed in a future release. "
                "Please migrate to 'APP_API_KEY'."
            )
        raw = (self.app_api_key or self.api_auth_token).strip()
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def admin_keys(self) -> List[str]:
        """Returns parsed list of admin API keys from APP_ADMIN_KEYS, or defaults to first key in api_keys."""
        raw = self.app_admin_keys.strip()
        if raw:
            return [k.strip() for k in raw.split(",") if k.strip()]
        keys = self.api_keys
        if keys:
            return [keys[0]]
        return []

    @property
    def rate_limit_per_minute(self) -> int:
        """Backward-compatible alias for rate_limit_per_min."""
        return self.rate_limit_per_min

    @rate_limit_per_minute.setter
    def rate_limit_per_minute(self, value: int):
        self.rate_limit_per_min = value

    @property
    def effective_rate_limit(self) -> int:
        """Returns configured requests per minute limit."""
        return self.rate_limit_per_min or 30


settings = Settings()
