import base64
import json
import os
import subprocess
from typing import List
from pydantic import Field, model_validator
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
    ENCRYPTION_MASTER_KEY: str | None = None
    TICK_SECRET: str | None = None
    USE_FAKE_SMTP: bool = True
    FAKE_SMTP_HOST: str = "localhost"
    FAKE_SMTP_PORT: int = 1025
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://vikas003dangi.github.io",
    ]

    ADMIN_EMAILS: str | None = None
    ADMIN_BOOTSTRAP_TOKEN: str | None = None

    # Platform System Relay (Google Apps Script Web App for platform transactional mail)
    SYSTEM_RELAY_URL: str | None = None
    SYSTEM_RELAY_TOKEN: str | None = None

    BREVO_API_KEY: str | None = None
    BREVO_SENDER_EMAIL: str = "noreply@mailorbit.io"

    SYSTEM_SMTP_HOST: str | None = None
    SYSTEM_SMTP_PORT: int = 587
    SYSTEM_SMTP_USER: str | None = None
    SYSTEM_SMTP_PASSWORD: str | None = None
    SYSTEM_SMTP_FROM: str | None = None

    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None

    TRUSTED_PROXY_COUNT: int = 1
    IS_BEHIND_CLOUDFLARE: bool = False
    COMMIT_HASH: str = Field(default_factory=get_commit_hash)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            # 1. Master Key Check: must exist and decode to 32 bytes
            if not self.ENCRYPTION_MASTER_KEY:
                raise ValueError("Production configuration error: ENCRYPTION_MASTER_KEY environment variable is required.")
            clean_key = self.ENCRYPTION_MASTER_KEY.strip()
            padded = clean_key + "=" * (-len(clean_key) % 4)
            try:
                try:
                    raw = base64.urlsafe_b64decode(padded.encode())
                except Exception:
                    raw = base64.b64decode(padded.encode())
                if len(raw) != 32:
                    raise ValueError(f"ENCRYPTION_MASTER_KEY must decode to exactly 32 raw bytes (AES-256), got {len(raw)} bytes.")
            except Exception as e:
                raise ValueError(f"Production configuration error: Invalid ENCRYPTION_MASTER_KEY format: {e}")

            # 2. Tick Secret Check: must exist, >= 16 chars, no dev placeholder
            if not self.TICK_SECRET or len(self.TICK_SECRET.strip()) < 16:
                raise ValueError("Production configuration error: TICK_SECRET is required and must be at least 16 characters.")
            if "change-in-prod" in self.TICK_SECRET.lower() or "dev-" in self.TICK_SECRET.lower():
                raise ValueError("Production configuration error: TICK_SECRET contains an insecure development placeholder.")
        return self

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

