"""
In-Memory Schedule Cache for MailOrbit Watchdog (/tick).

Caches upcoming batch due times (`next_due_at`) in memory so that recurring
/tick pings answer 'standby' with ZERO database queries whenever no jobs are due.
This allows Neon Serverless PostgreSQL to remain suspended during idle periods.
"""

from datetime import datetime, time, timedelta, timezone
import logging
from typing import Optional
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from packages.shared.schema import Batch, JobModel, User

logger = logging.getLogger("mailorbit.schedule_cache")

DAY_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}


def compute_next_batch_run_utc(
    scheduled_days: list,
    scheduled_time_str: str,
    user_tz_str: str,
    now_utc: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Computes the next upcoming run time in UTC for a given schedule and user timezone.
    If today is an active day and the scheduled time has arrived/passed, returns the target
    timestamp so that is_tick_due() evaluates to True and the batch runs without delay.
    """
    ref_utc = now_utc or datetime.now(timezone.utc)
    try:
        user_tz = ZoneInfo(user_tz_str or "UTC")
    except Exception:
        user_tz = ZoneInfo("UTC")

    local_now = ref_utc.astimezone(user_tz)

    try:
        parts = (scheduled_time_str or "10:00").strip().split(":")
        target_hour = int(parts[0])
        target_minute = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        target_hour, target_minute = 10, 0

    target_time = time(hour=target_hour, minute=target_minute)
    allowed_days = [d.lower()[:3] for d in (scheduled_days or ["mon", "tue", "wed", "thu", "fri"])]

    # 1. Check if today is an allowed day
    today_date = local_now.date()
    today_day_name = DAY_MAP[today_date.weekday()]
    if today_day_name in allowed_days:
        today_target_dt = datetime.combine(today_date, target_time, tzinfo=user_tz)
        # If target time is later today or has already arrived today, return it
        return today_target_dt.astimezone(timezone.utc)

    # 2. Check upcoming future days (1 through 7)
    for day_offset in range(1, 8):
        candidate_date = (local_now + timedelta(days=day_offset)).date()
        candidate_day_name = DAY_MAP[candidate_date.weekday()]

        if candidate_day_name in allowed_days:
            candidate_dt_local = datetime.combine(candidate_date, target_time, tzinfo=user_tz)
            return candidate_dt_local.astimezone(timezone.utc)

    return None


class ScheduleCache:
    def __init__(self):
        self.next_due_at: Optional[datetime] = None
        self.has_pending_jobs: bool = False
        self.last_refreshed_at: Optional[datetime] = None

    def is_tick_due(self, now_utc: Optional[datetime] = None) -> bool:
        """
        Pure in-memory check. Returns True if a database check/worker run is required.
        Returns False if the system is completely idle (0 DB queries required).
        """
        if self.has_pending_jobs:
            return True

        if self.next_due_at is None:
            # No batches scheduled at all
            return False

        ref = now_utc or datetime.now(timezone.utc)
        return ref >= self.next_due_at

    def refresh_from_db(
        self,
        session: Session,
        user_id: Optional[uuid.UUID] = None,
        now_utc: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Queries database to find earliest next run time and any pending jobs,
        then caches the result in memory.
        """
        now = now_utc or datetime.now(timezone.utc)

        # 1. Check if there are unhandled jobs in the queue
        jobs_query = session.query(JobModel).filter(JobModel.status.in_(["PENDING", "RUNNING"]))
        self.has_pending_jobs = (jobs_query.count() > 0) if user_id is None else False

        # 2. Query active or scheduled batches
        batch_query = (
            session.query(Batch, User.timezone)
            .join(User, Batch.user_id == User.id)
            .filter(Batch.status.in_(["ACTIVE", "PENDING"]))
        )
        if user_id is not None:
            batch_query = batch_query.filter(Batch.user_id == user_id)

        batches = batch_query.all()

        earliest_due: Optional[datetime] = None

        for batch, tz_str in batches:
            next_run = compute_next_batch_run_utc(
                scheduled_days=batch.scheduled_days,
                scheduled_time_str=batch.scheduled_time,
                user_tz_str=tz_str,
                now_utc=now,
            )
            if next_run:
                if earliest_due is None or next_run < earliest_due:
                    earliest_due = next_run

        self.next_due_at = earliest_due
        self.last_refreshed_at = now
        logger.info(
            "ScheduleCache refreshed: next_due_at=%s, has_pending_jobs=%s",
            self.next_due_at.isoformat() if self.next_due_at else "None",
            self.has_pending_jobs,
        )
        return self.next_due_at


# Global singleton cache
schedule_cache = ScheduleCache()

