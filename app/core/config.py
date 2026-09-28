
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Metadata
    PROJECT_NAME: str = "EVE Healthcare Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://eve_user:eve_password@localhost:5432/eve_healthcare_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://eve_user:eve_password@localhost:5432/eve_healthcare_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Security & JWT
    JWT_SECRET_KEY: str = "eve-healthcare-super-secret-jwt-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Webhook
    WEBHOOK_SECRET: str = "whsec_eve_healthcare_mock_webhook_secret_key_2026"

    # Seed User Credentials
    SEED_ADMIN_EMAIL: str = "admin@evehealthcare.com"
    SEED_ADMIN_PASSWORD: str = "AdminPassword123!"
    SEED_USER_EMAIL: str = "user@evehealthcare.com"
    SEED_USER_PASSWORD: str = "UserPassword123!"

    # CORS Settings
    CORS_ORIGINS: str | list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()
