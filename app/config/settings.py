"""Secure application settings configuration."""

from functools import lru_cache
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with secure handling of sensitive data."""

    # Application
    app_name: str = "PowerCV"
    version: str = "2.0.0"
    environment: str = "development"
    debug: bool = False

    # Security - Use secure defaults
    secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    sentry_dsn: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None

    # API Keys (sensitive - never log these)
    api_key: Optional[str] = None  # Deepseek
    deepseek_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Case-insensitive aliases for common environment variable variations
    CEREBRAS_API_KEY: Optional[str] = None  # Uppercase variant
    DEEPSEEK_API_KEY: Optional[str] = None  # Uppercase Deepseek variant
    API_KEY: Optional[str] = None  # Uppercase Deepseek variant
    OPENAI_API_KEY: Optional[str] = None  # Uppercase OpenAI variant
    SENTRY_DSN: Optional[str] = None  # Uppercase Sentry DSN variant
    POSTGRES_USER: Optional[str] = None  # Uppercase PostgreSQL user
    POSTGRES_PASSWORD: Optional[str] = None  # Uppercase PostgreSQL password
    POSTGRES_DB: Optional[str] = None  # Uppercase PostgreSQL database
    POSTGRES_HOST: Optional[str] = None  # Uppercase PostgreSQL host
    POSTGRES_PORT: Optional[int] = None  # Uppercase PostgreSQL port
    POSTGRES_USER: Optional[str] = None  # Uppercase PostgreSQL user
    POSTGRES_PASSWORD: Optional[str] = None  # Uppercase PostgreSQL password
    POSTGRES_DB: Optional[str] = None  # Uppercase PostgreSQL database
    POSTGRES_HOST: Optional[str] = None  # Uppercase PostgreSQL host
    POSTGRES_PORT: Optional[int] = None  # Uppercase PostgreSQL port
    POSTGRES_USER: Optional[str] = None  # Uppercase PostgreSQL user
    POSTGRES_PASSWORD: Optional[str] = None  # Uppercase PostgreSQL password
    POSTGRES_DB: Optional[str] = None  # Uppercase PostgreSQL database
    POSTGRES_HOST: Optional[str] = None  # Uppercase PostgreSQL host
    POSTGRES_PORT: Optional[int] = None  # Uppercase PostgreSQL port
    API_KEY_UPPER: Optional[str] = None  # Alternative uppercase variant
    OPENAI_API_KEY_UPPER: Optional[str] = None  # Alternative uppercase variant

    # Database
    mongodb_uri: str = "mongodb://localhost:27017/powercv"
    database_name: str = "powercv"

    @property
    def mongodb_db(self) -> str:
        """Alias for database_name for backward compatibility."""
        return self.database_name

    # Redis (for caching and rate limiting)
    redis_url: Optional[str] = None

    # External services
    sentry_dsn: Optional[str] = None

    # File upload settings
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "/tmp/uploads"

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # User identity settings
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    USER_FIRST_NAME: Optional[str] = None
    USER_LAST_NAME: Optional[str] = None

    def model_post_init(self, __context):
        """Normalize API key variants after initialization."""
        # Merge uppercase variants into lowercase ones for backward compatibility
        if self.CEREBRAS_API_KEY and not self.cerebras_api_key:
            self.cerebras_api_key = self.CEREBRAS_API_KEY
        if self.DEEPSEEK_API_KEY and not self.deepseek_api_key:
            self.deepseek_api_key = self.DEEPSEEK_API_KEY
        if self.API_KEY_UPPER and not self.api_key:
            self.api_key = self.API_KEY_UPPER
        if self.OPENAI_API_KEY_UPPER and not self.openai_api_key:
            self.openai_api_key = self.OPENAI_API_KEY_UPPER

        # Normalize user identity
        if self.USER_FIRST_NAME and not self.user_first_name:
            self.user_first_name = self.USER_FIRST_NAME
        if self.USER_LAST_NAME and not self.user_last_name:
            self.user_last_name = self.USER_LAST_NAME

        # Validate required secrets in production
        if self.environment == "production" and not self.secret_key:
            raise ValueError(
                "SECRET_KEY must be set in production environment")

        # Merge Deepseek API key
        if self.DEEPSEEK_API_KEY and not self.deepseek_api_key:
            self.deepseek_api_key = self.DEEPSEEK_API_KEY

        # Merge Sentry DSN
        if self.SENTRY_DSN and not self.sentry_dsn:
            self.sentry_dsn = self.SENTRY_DSN

        # Merge PostgreSQL configuration (consolidated to avoid duplication)
        if self.POSTGRES_USER and not self.postgres_user:
            self.postgres_user = self.POSTGRES_USER
        if self.POSTGRES_PASSWORD and not self.postgres_password:
            self.postgres_password = self.POSTGRES_PASSWORD
        if self.POSTGRES_DB and not self.postgres_db:
            self.postgres_db = self.POSTGRES_DB
        if self.POSTGRES_HOST and not self.postgres_host:
            self.postgres_host = self.POSTGRES_HOST
        if self.POSTGRES_PORT and not self.postgres_port:
            self.postgres_port = self.POSTGRES_PORT

        # Merge PostgreSQL configuration
        if self.POSTGRES_USER and not self.postgres_user:
            self.postgres_user = self.POSTGRES_USER
        if self.POSTGRES_PASSWORD and not self.postgres_password:
            self.postgres_password = self.POSTGRES_PASSWORD
        if self.POSTGRES_DB and not self.postgres_db:
            self.postgres_db = self.POSTGRES_DB
        if self.POSTGRES_HOST and not self.postgres_host:
            self.postgres_host = self.POSTGRES_HOST
        if self.POSTGRES_PORT and not self.postgres_port:
            self.postgres_port = self.POSTGRES_PORT

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,  # Strict case-sensitive environment variables
        extra="ignore",  # Allow extra environment variables
        # Fields that contain sensitive information
    )

    def __repr__(self):
        """Secure repr that doesn't expose sensitive data."""
        # Only show non-sensitive fields
        safe_fields = {
            "secret_key",
            "api_key",
            "deepseek_api_key",
            "cerebras_api_key",
            "openai_api_key",
            "CEREBRAS_API_KEY",
            "DEEPSEEK_API_KEY",
            "API_KEY_UPPER",
            "OPENAI_API_KEY_UPPER",
            "mongodb_uri",
            "redis_url",
            "sentry_dsn",
        }

        safe_attrs = {}
        for field_name, field_info in self.model_fields.items():
            if field_name not in safe_fields:
                safe_attrs[field_name] = getattr(self, field_name)

        attrs_str = ", ".join(f"{k}={v!r}" for k, v in safe_attrs.items())
        return f"Settings({attrs_str})"

    def get_database_config(self) -> dict:
        """Get database configuration (without exposing credentials in logs)."""
        return {
            "mongodb": {
                "uri": self._mask_mongodb_uri(self.mongodb_uri),
                "database": self.database_name,
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
