from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — superuser (used for migrations, seeding, pre-auth)
    DATABASE_URL: str = "postgresql+asyncpg://bryton:bryton_dev@db:5432/bryton"
    # App role (non-superuser, used for tenant-scoped RLS queries)
    APP_DATABASE_URL: str = "postgresql+asyncpg://bryton_app:bryton_dev@db:5432/bryton"

    # Azure Blob Storage — empty string means health check skips Blob probe
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:80", "http://localhost:3000"]'

    # Email (SMTP)
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@brytonai.com"
    SMTP_USE_TLS: bool = False

    # Frontend URL (used in email links)
    FRONTEND_URL: str = "http://localhost:80"

    # Cookie security — False for dev (HTTP), True for prod (HTTPS)
    COOKIE_SECURE: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
