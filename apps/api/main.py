import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from apps.api.config import settings
from apps.api.diagnostics import run_egress_check
from apps.api.routers import ai_keys, auth, batches, contacts, profile, purposes, senders
from apps.worker import InMemoryJobQueue, WorkerRunner
from packages.shared.models import EgressReport, HealthResponse, TickResponse

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger("mailorbit.api")

app = FastAPI(
    title="MailOrbit API",
    description="Backend API for MailOrbit cold-email outreach platform",
    version="0.1.0",
)

# CORS Configuration for frontend (Static export on GitHub Pages or localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Feature Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(senders.router)
app.include_router(ai_keys.router)
app.include_router(purposes.router)
app.include_router(batches.router)
app.include_router(contacts.router)

# Initialize in-process worker queue & runner
queue = InMemoryJobQueue()
worker = WorkerRunner(queue=queue)


def verify_tick_secret(
    x_tick_secret: Optional[str] = Header(None, alias="X-Tick-Secret"),
    secret: Optional[str] = Query(None),
) -> None:
    provided = x_tick_secret or secret
    if not provided or provided != settings.TICK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing tick authentication secret",
        )


@app.get("/", include_in_schema=False)
def root():
    """Redirects root visits to the interactive API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def get_health():
    """Unprotected health check endpoint for uptime pingers and Render."""
    return HealthResponse(
        status="ok",
        app="mailorbit-api",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
    )


@app.post("/api/v1/tick", response_model=TickResponse, tags=["Watchdog"])
def run_tick(
    batch_size: int = Query(10, ge=1, le=100),
    _=Security(verify_tick_secret),
):
    """
    Protected tick endpoint called by cron-job.org / watchdog.
    Triggers in-process worker processing of due batches and scheduled emails.
    """
    processed = worker.tick(batch_size=batch_size)
    return TickResponse(
        status="ok",
        jobs_claimed=processed,
        jobs_processed=processed,
        message=f"Tick processed {processed} jobs",
    )


@app.get("/api/v1/diagnostics/egress", response_model=EgressReport, tags=["Diagnostics"])
def get_egress_diagnostics(
    _=Security(verify_tick_secret),
):
    """
    Protected diagnostic endpoint testing outbound network egress:
    1. TCP smtp.gmail.com:587
    2. TCP script.google.com:443
    3. HTTPS GET https://script.google.com
    """
    return run_egress_check()
