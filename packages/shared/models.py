from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "mailorbit-api"
    version: str = "0.1.0"
    environment: str = "development"
    timestamp: datetime = Field(default_factory=utc_now)

class DiagnosticItem(BaseModel):
    status: str  # PASS / FAIL
    detail: str

class EgressReport(BaseModel):
    server_time: datetime = Field(default_factory=utc_now)
    smtp_587: DiagnosticItem
    script_tcp_443: DiagnosticItem
    script_https_get: DiagnosticItem
    relay_ready: bool
    note: str

class TickResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=utc_now)
    jobs_claimed: int = 0
    jobs_processed: int = 0
    message: str = "Watchdog tick completed successfully"
