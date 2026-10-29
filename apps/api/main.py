from contextlib import asynccontextmanager
import logging
import os
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.dependencies import get_current_user, get_db
from apps.api.services.schedule_cache import schedule_cache
from packages.shared.schema import User
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

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Prime in-memory schedule cache on startup
    try:
        with session_factory() as session:
            schedule_cache.refresh_from_db(session)
    except Exception as e:
        logger.warning("Failed to prime schedule cache on startup: %s", e)
    yield


app = FastAPI(
    title="MailOrbit API",
    description="Backend API for MailOrbit cold-email outreach platform",
    version="0.1.0",
    lifespan=lifespan,
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


@app.get("/status", response_class=HTMLResponse, tags=["System"], include_in_schema=False)
def status_page(db: Session = Depends(get_db)):
    """System architecture and isolated status diagnostics page."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MailOrbit System Architecture & Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{ background: #0b0f19; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 40px 20px; }}
    .container {{ max-width: 680px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    h1 {{ font-size: 1.5rem; margin: 0 0 6px; color: #ffffff; }}
    .status-badge {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 20px; background: rgba(34, 197, 94, 0.15); color: #4ade80; font-weight: 600; font-size: 0.85rem; border: 1px solid #22c55e; margin: 16px 0 24px; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }}
    .stack-list {{ list-style: none; padding: 0; margin: 0 0 28px; }}
    .stack-item {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #1f2937; font-size: 0.9rem; }}
    .stack-name {{ color: #e2e8f0; font-weight: 500; }}
    .stack-val {{ color: #38bdf8; font-size: 0.85rem; font-weight: 600; }}
    .btn {{ display: inline-block; background: #0284c7; color: #fff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>MailOrbit System Architecture & Status</h1>
    <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">Isolated infrastructure status and connection telemetry.</p>
    <div class="status-badge"><span class="dot"></span> All Systems Operational</div>
    <ul class="stack-list">
      <li class="stack-item"><span class="stack-name">Unified Host Runtime</span><span class="stack-val">Render Web Service (Oregon)</span></li>
      <li class="stack-item"><span class="stack-name">Web Application</span><span class="stack-val">Mounted at root "/" (Next.js Static Export)</span></li>
      <li class="stack-item"><span class="stack-name">Relational Database</span><span class="stack-val">Neon PostgreSQL 16 (Ohio) - {'Connected' if db_ok else 'Degraded'}</span></li>
      <li class="stack-item"><span class="stack-name">Outbound Egress Relay</span><span class="stack-val">Google Apps Script HTTPS:443 (10% Safety Pause)</span></li>
      <li class="stack-item"><span class="stack-name">Watchdog Scheduler</span><span class="stack-val">cron-job.org /tick (Header-only auth, 10m active 06:00-24:00 IST)</span></li>
      <li class="stack-item"><span class="stack-name">Keepalive Monitor</span><span class="stack-val">Disabled (UptimeRobot paused; compute sleeps 00:00-06:00 IST)</span></li>
      <li class="stack-item"><span class="stack-name">Attachment Storage</span><span class="stack-val">Cloudinary Storage (Signed URLs)</span></li>
    </ul>
    <a href="/" class="btn">← Back to MailOrbit App</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)


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
    - If in-memory schedule cache confirms no batches are due and no jobs pending:
      Answers 'standby' immediately with ZERO database queries (allows Neon compute to suspend).
    - If batches or jobs are due:
      Evaluates due batches, claims and executes jobs, then refreshes the schedule cache.
    """
    # In-memory check for zero DB query standby
    if schedule_cache.last_refreshed_at is not None and not schedule_cache.is_tick_due():
        return TickResponse(
            status="standby",
            batches_queued=0,
            jobs_claimed=0,
            jobs_processed=0,
            message="Tick status: standby (0 DB queries; in-memory schedule cache confirmed no batches due)",
        )

    batches_queued = 0
    try:
        with session_factory() as session:
            sched_result = evaluate_all_due_batches(session=session, queue=queue)
            batches_queued = sched_result.get("batches_queued", 0)
            schedule_cache.refresh_from_db(session)
    except Exception as e:
        logger.exception("Error during scheduler evaluation in tick: %s", e)

    processed = worker.tick(batch_size=batch_size)
    if processed > 0:
        try:
            with session_factory() as session:
                schedule_cache.refresh_from_db(session)
        except Exception:
            pass

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
    current_user: User = Depends(get_current_user),
):
    """
    Protected diagnostic endpoint testing outbound network egress:
    1. TCP smtp.gmail.com:587
    2. TCP script.google.com:443
    3. HTTPS GET https://script.google.com
    """
    return run_egress_check()


# Mount static build of Next.js frontend at root "/"
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
