from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from apps.worker.interface import JobQueue
from packages.shared.schema import Batch, User

logger = logging.getLogger("mailorbit.scheduler")


def get_user_local_datetime(user_timezone: Optional[str], ref_utc: Optional[datetime] = None) -> datetime:
    """Returns the current datetime in the user's local timezone."""
    ref = ref_utc or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    try:
        tz = ZoneInfo(user_timezone or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return ref.astimezone(tz)


def is_batch_scheduled_for_today(batch: Batch, local_dt: datetime) -> bool:
    """
    Checks if today (in user's timezone) is an active send day for this batch.
    batch.scheduled_days is a list like ['mon', 'tue', 'wed', 'thu', 'fri'].
    """
    if not batch.scheduled_days:
        return True

    current_day = local_dt.strftime("%a").lower()[:3]
    active_days = [d.lower()[:3] for d in batch.scheduled_days]
    return current_day in active_days


def is_batch_time_reached(batch: Batch, local_dt: datetime) -> bool:
    """
    Checks if the scheduled send time (e.g. '10:00') has arrived or passed today.
    """
    if not batch.scheduled_time:
        return True

    current_time_str = local_dt.strftime("%H:%M")
    scheduled_time_str = batch.scheduled_time.strip()
    return current_time_str >= scheduled_time_str


def evaluate_due_batches_for_user(
    session: Session,
    user: User,
    queue: JobQueue,
    ref_utc: Optional[datetime] = None,
) -> List[Batch]:
    """
    Evaluates pending batches for a user.
    Enforces 'N emails per day at time T on days D':
    - Groups batches by purpose_id.
    - Slices one batch per purpose per calendar day.
    - Enqueues due batch into JobQueue and sets batch.status = 'QUEUED'.
    """
    local_dt = get_user_local_datetime(user.timezone, ref_utc)
    today_date = local_dt.date()

    # Query all batches for this user to inspect today's campaign state
    user_batches = (
        session.query(Batch)
        .filter(Batch.user_id == user.id)
        .all()
    )

    # Find which purposes already had a batch run/queued today or are currently active
    busy_purposes = set()
    for b in user_batches:
        if b.status in ("QUEUED", "ACTIVE"):
            busy_purposes.add(b.purpose_id)
        elif b.status == "COMPLETED" and b.updated_at:
            b_updated = b.updated_at
            if b_updated.tzinfo is None:
                b_updated = b_updated.replace(tzinfo=timezone.utc)
            b_local_date = b_updated.astimezone(local_dt.tzinfo).date()
            if b_local_date == today_date:
                busy_purposes.add(b.purpose_id)

    # Query pending batches ordered by sequence position and creation time
    pending_batches = (
        session.query(Batch)
        .filter(
            Batch.user_id == user.id,
            Batch.status == "PENDING",
        )
        .order_by(Batch.position.asc(), Batch.created_at.asc())
        .all()
    )

    queued_batches: List[Batch] = []

    # Map by purpose to pick only the earliest pending batch per purpose
    earliest_by_purpose: Dict[Optional[uuid.UUID], Batch] = {}
    for pb in pending_batches:
        if pb.purpose_id not in busy_purposes and pb.purpose_id not in earliest_by_purpose:
            earliest_by_purpose[pb.purpose_id] = pb

    for purpose_id, candidate in earliest_by_purpose.items():
        if not is_batch_scheduled_for_today(candidate, local_dt):
            logger.debug("Batch %s not scheduled for today (%s)", candidate.name, local_dt.strftime("%a"))
            continue

        if not is_batch_time_reached(candidate, local_dt):
            logger.debug(
                "Batch %s scheduled time %s not reached (current: %s)",
                candidate.name,
                candidate.scheduled_time,
                local_dt.strftime("%H:%M"),
            )
            continue

        # Mark batch as QUEUED and enqueue in job queue
        candidate.status = "QUEUED"
        session.commit()

        queue.enqueue(
            job_type="send_batch",
            payload={"batch_id": str(candidate.id)},
        )
        queued_batches.append(candidate)
        logger.info(
            "Enqueued scheduled batch '%s' (id=%s) for user %s",
            candidate.name,
            candidate.id,
            user.id,
        )

    return queued_batches


def evaluate_all_due_batches(
    session: Session,
    queue: JobQueue,
    ref_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Evaluates all active users and enqueues due batches into the JobQueue.
    """
    users = session.query(User).filter(User.is_active == True).all()
    total_queued = 0
    total_evaluated_users = len(users)

    for user in users:
        queued = evaluate_due_batches_for_user(session, user, queue, ref_utc)
        total_queued += len(queued)

    return {
        "evaluated_users": total_evaluated_users,
        "batches_queued": total_queued,
    }

