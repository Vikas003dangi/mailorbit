import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from apps.api.config import settings
from apps.api.diagnostics import run_egress_check
from apps.api.routers import (
    admin,
    ai_keys,
    attachments,
    auth,
    batches,
    contacts,
    profile,
    purposes,
    senders,
    unsubscribe,
)
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
    allow_origin_regex=r"https?://.*",
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
app.include_router(attachments.router)
app.include_router(unsubscribe.router)
app.include_router(admin.router)

# Initialize in-process worker queue & runner
import uuid
from packages.shared.db import create_db_engine, create_session_factory
from apps.worker import (
    Job,
    PostgresJobQueue,
    WorkerRunner,
    dispatch_batch,
    evaluate_all_due_batches,
)

try:
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)
    queue = PostgresJobQueue(session_factory=session_factory)
except Exception as e:
    logger.warning("Falling back to InMemoryJobQueue: %s", e)
    from apps.worker import InMemoryJobQueue
    queue = InMemoryJobQueue()

worker = WorkerRunner(queue=queue)


def handle_send_batch(job: Job):
    batch_id = uuid.UUID(job.payload["batch_id"])
    with session_factory() as session:
        return dispatch_batch(session=session, batch_id=batch_id)


worker.register_handler("send_batch", handle_send_batch)


def verify_tick_secret(
    x_tick_secret: Optional[str] = Header(None, alias="X-Tick-Secret"),
) -> None:
    if not x_tick_secret or x_tick_secret != settings.TICK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Tick-Secret header",
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


@app.api_route("/api/v1/tick", methods=["GET", "POST"], response_model=TickResponse, tags=["Watchdog"])
def run_tick(
    batch_size: int = Query(10, ge=1, le=100),
    _=Security(verify_tick_secret),
):
    """
    Protected tick endpoint called by cron-job.org / watchdog.
    Triggers:
    1. Scheduler evaluation: evaluates due scheduled batches across all users based on timezone, days, and send time.
    2. Worker execution: claims queued jobs from PostgreSQL queue and dispatches them.
    """
    batches_queued = 0
    try:
        with session_factory() as session:
            sched_result = evaluate_all_due_batches(session=session, queue=queue)
            batches_queued = sched_result.get("batches_queued", 0)
    except Exception as e:
        logger.exception("Error during scheduler evaluation in tick: %s", e)

    processed = worker.tick(batch_size=batch_size)
    status_str = "standby" if (batches_queued == 0 and processed == 0) else "ok"
    return TickResponse(
        status=status_str,
        batches_queued=batches_queued,
        jobs_claimed=processed,
        jobs_processed=processed,
        message=f"Tick status: {status_str} (queued {batches_queued} batches, processed {processed} jobs)",
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
