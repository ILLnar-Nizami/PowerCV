"""Secure application settings configuration."""

from functools import lru_cache
from typing import List, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Unified application settings with secure handling of sensitive data."""

    # Application settings
    app_name: str = Field(default="PowerCV", validation_alias=AliasChoices("APP_NAME"))
    version: str = Field(
        default="3.0.0-beta", validation_alias=AliasChoices("VERSION", "APP_VERSION")
    )
    environment: str = Field(
        default="development", validation_alias=AliasChoices("ENVIRONMENT", "ENV")
    )
    debug: bool = Field(default=False, validation_alias=AliasChoices("DEBUG"))

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        """Parse debug field to handle various boolean representations."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on", "enable", "enabled")
        return bool(v)

    # Server settings
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HOST"))
    port: int = Field(default=8000, validation_alias=AliasChoices("PORT"))
    reload: bool = Field(default=False, validation_alias=AliasChoices("RELOAD"))

    # Security settings
    secret_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SECRET_KEY")
    )
    algorithm: str = Field(
        default="HS256", validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM")
    )
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_EXPIRATION_HOURS"
        ),
    )
    sentry_dsn: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SENTRY_DSN")
    )

    # Database settings - MongoDB
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/powercv",
        validation_alias=AliasChoices("MONGODB_URI"),
    )
    mongodb_db: str = Field(
        default="powercv", validation_alias=AliasChoices("MONGODB_DB", "DATABASE_NAME")
    )

    @property
    def database_name(self) -> str:
        """Alias for mongodb_db for backward compatibility."""
        return self.mongodb_db

    # Database settings - PostgreSQL
    postgres_user: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_USER")
    )
    postgres_password: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_PASSWORD")
    )
    postgres_db: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_DB")
    )
    postgres_host: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("POSTGRES_HOST")
    )
    postgres_port: int = Field(
        default=5432, validation_alias=AliasChoices("POSTGRES_PORT")
    )

    # Redis settings (for caching and rate limiting)
    redis_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("REDIS_URL")
    )
    redis_host: str = Field(
        default="localhost", validation_alias=AliasChoices("REDIS_HOST")
    )
    redis_port: int = Field(default=6379, validation_alias=AliasChoices("REDIS_PORT"))
    redis_db: int = Field(default=0, validation_alias=AliasChoices("REDIS_DB"))
    redis_password: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("REDIS_PASSWORD")
    )

    # AI Provider settings
    # Deepseek
    api_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("API_KEY", "DEEPSEEK_API_KEY")
    )
    deepseek_api_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("DEEPSEEK_API_KEY")
    )

    # Cerebras
    cerebras_api_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("CEREBRAS_API_KEY")
    )
    cerebras_api_base: str = Field(
        default="https://api.cerebras.ai/v1",
        validation_alias=AliasChoices("CEREBRAS_API_BASE"),
    )
    cerebras_model: str = Field(
        default="llama3.1-8b", validation_alias=AliasChoices("CEREBRAS_MODEL")
    )

    # OpenAI
    openai_api_key: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY")
    )
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_API_BASE"),
    )
    openai_model: str = Field(
        default="gpt-4", validation_alias=AliasChoices("OPENAI_MODEL")
    )

    # Ollama (local models)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL"),
    )
    ollama_model: str = Field(
        default="llama2", validation_alias=AliasChoices("OLLAMA_MODEL")
    )

    # CORS settings
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://localhost:8000",
        ],
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True, validation_alias=AliasChoices("RATE_LIMIT_ENABLED")
    )
    rate_limit_requests_per_minute: int = Field(
        default=100,
        validation_alias=AliasChoices(
            "RATE_LIMIT_REQUESTS_PER_MINUTE", "RATE_LIMIT_PER_MINUTE"
        ),
    )
    rate_limit_requests_per_hour: int = Field(
        default=1000,
        validation_alias=AliasChoices(
            "RATE_LIMIT_REQUESTS_PER_HOUR", "RATE_LIMIT_PER_HOUR"
        ),
    )

    # File upload settings
    max_file_size: int = Field(
        # 10MB
        default=10 * 1024 * 1024,
        validation_alias=AliasChoices("MAX_FILE_SIZE"),
    )
    allowed_file_types: List[str] = Field(
        default=["pdf", "doc", "docx", "txt"],
        validation_alias=AliasChoices("ALLOWED_FILE_TYPES"),
    )
    upload_dir: str = Field(
        default="uploads", validation_alias=AliasChoices("UPLOAD_DIR")
    )

    # Logging settings
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        validation_alias=AliasChoices("LOG_FORMAT"),
    )

    # AI Model tiers configuration
    fast_model: str = Field(
        default="llama3.1-8b", validation_alias=AliasChoices("FAST_MODEL")
    )
    balanced_model: str = Field(
        default="llama3.1-8b", validation_alias=AliasChoices("BALANCED_MODEL")
    )
    quality_model: str = Field(
        default="gpt-4", validation_alias=AliasChoices("QUALITY_MODEL")
    )

    # External services (n8n, SMTP)
    smtp_host: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SMTP_HOST")
    )
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("SMTP_PORT"))
    smtp_user: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SMTP_USER")
    )
    smtp_password: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("SMTP_PASSWORD")
    )
    n8n_webhook_url: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("N8N_WEBHOOK_URL")
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_database_config(self) -> dict:
        """Get database configuration for logging (without exposing credentials)."""
        return {
            "mongodb": {
                "uri": self._mask_mongodb_uri(self.mongodb_uri),
                "database": self.mongodb_db,
            },
            "postgres": {
                "user": self.postgres_user,
                "password": "***" if self.postgres_password else None,
                "db": self.postgres_db,
                "host": self.postgres_host,
                "port": self.postgres_port,
            },
        }

    @staticmethod
    def _mask_mongodb_uri(uri: str) -> str:
        """Mask credentials in MongoDB URI for safe logging."""
        import re

        return re.sub(r"://([^:]+):([^@]+)@", "://***:***@", uri)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
