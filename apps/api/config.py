import json
import os
import subprocess
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_commit_hash() -> str:
    commit = os.getenv("RENDER_GIT_COMMIT")
    if commit:
        return commit[:7]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


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

    ADMIN_EMAILS: str = "vikassdangi@gmail.com,vd19055@gmail.com"
    ADMIN_BOOTSTRAP_TOKEN: str | None = None
    BREVO_API_KEY: str | None = None
    BREVO_SENDER_EMAIL: str = "noreply@mailorbit.io"

    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None

    TRUSTED_PROXY_COUNT: int = 1
    IS_BEHIND_CLOUDFLARE: bool = False
    COMMIT_HASH: str = Field(default_factory=get_commit_hash)

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

