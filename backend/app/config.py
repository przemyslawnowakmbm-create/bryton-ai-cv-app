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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:80", "http://localhost:3000"]'

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
