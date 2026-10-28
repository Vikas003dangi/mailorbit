import json
import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql://mailorbit:mailorbit_dev_password@localhost:5432/mailorbit"
    DATABASE_URL_UNPOOLED: str | None = None
    ENCRYPTION_MASTER_KEY: str = "k9+F2L6qW4mP0sU8yX1zB7cE3gH5jN9rT2vY4aC6eI8="
    TICK_SECRET: str = "dev-watchdog-tick-secret-change-in-prod"
    USE_FAKE_SMTP: bool = True
    FAKE_SMTP_HOST: str = "localhost"
    FAKE_SMTP_PORT: int = 1025
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://vikas003dangi.github.io",
    ]

    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

