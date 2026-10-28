from datetime import datetime, timezone
import uuid
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from apps.worker.interface import Job
from apps.worker.queue import InMemoryJobQueue
from apps.worker.scheduler import (
    evaluate_all_due_batches,
    evaluate_due_batches_for_user,
    get_user_local_datetime,
    is_batch_scheduled_for_today,
    is_batch_time_reached,
)
from packages.shared.auth import hash_password
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Batch, Contact, Purpose, User


def create_test_user_and_purpose(session, tz_name="UTC"):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"sched_user_{unique}@example.com",
        password_hash=hash_password("SecretPassword123!"),
        timezone=tz_name,
        is_active=True,
    )
    session.add(user)
    session.flush()

    purpose = Purpose(
        user_id=user.id,
        name="Automated Sched Campaign",
        default_subject_template="Outreach from {name}",
        default_body_template="Hi {name}, checking in.",
        is_active=True,
    )
    session.add(purpose)
    session.flush()
    session.commit()
    return user, purpose


def test_timezone_and_schedule_rules():
    """
    Unit test for scheduler helper functions:
    - Timezone conversion
    - Day matching
    - Send time matching
    """
    # 2026-10-28 05:00:00 UTC is Wednesday 10:30:00 in Asia/Kolkata (UTC+5:30)
    ref_utc = datetime(2026, 10, 28, 5, 0, 0, tzinfo=timezone.utc)

    kolkata_dt = get_user_local_datetime("Asia/Kolkata", ref_utc)
    assert kolkata_dt.strftime("%a").lower() == "wed"
    assert kolkata_dt.strftime("%H:%M") == "10:30"

    ny_dt = get_user_local_datetime("America/New_York", ref_utc)
    # 05:00 UTC is 01:00 AM EDT (UTC-4)
    assert ny_dt.strftime("%H:%M") == "01:00"

    # Batch scheduled for weekdays (mon, tue, wed, thu, fri)
    batch = Batch(
        name="Weekday Batch",
        scheduled_days=["mon", "tue", "wed", "thu", "fri"],
        scheduled_time="10:00",
    )
    assert is_batch_scheduled_for_today(batch, kolkata_dt) is True
    assert is_batch_time_reached(batch, kolkata_dt) is True  # 10:30 >= 10:00

    # Batch scheduled for weekend
    weekend_batch = Batch(
        name="Weekend Batch",
        scheduled_days=["sat", "sun"],
        scheduled_time="10:00",
    )
    assert is_batch_scheduled_for_today(weekend_batch, kolkata_dt) is False

    # Batch scheduled for later in the day (e.g. 14:00)
    later_batch = Batch(
        name="Afternoon Batch",
        scheduled_days=["wed"],
        scheduled_time="14:00",
    )
    assert is_batch_scheduled_for_today(later_batch, kolkata_dt) is True
    assert is_batch_time_reached(later_batch, kolkata_dt) is False  # 10:30 < 14:00


def test_scheduler_evaluates_and_enqueues_due_batch():
    """
    TRD Milestone M6 Core Acceptance Test:
    - Slices and enqueues due batches based on user timezone, scheduled days, and time.
    - Slices one batch per day per purpose (preserves daily limit).
    - Guarantees strict idempotency on repeated ticks.
    """
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    queue = InMemoryJobQueue()

    # Wednesday 10:30 UTC
    ref_wednesday = datetime(2026, 10, 28, 10, 30, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        user, purpose = create_test_user_and_purpose(session, tz_name="UTC")

        # Create 2 pending batches for this purpose
        batch1 = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="Day 1 Batch",
            size=10,
            position=1,
            scheduled_days=["mon", "tue", "wed", "thu", "fri"],
            scheduled_time="09:00",  # Due! (10:30 >= 09:00)
            status="PENDING",
        )
        batch2 = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="Day 2 Batch",
            size=10,
            position=2,
            scheduled_days=["mon", "tue", "wed", "thu", "fri"],
            scheduled_time="09:00",
            status="PENDING",
        )
        session.add_all([batch1, batch2])
        session.commit()
        user_id = user.id
        b1_id, b2_id = batch1.id, batch2.id

    # 1. Run scheduler evaluation
    with session_factory() as session:
        user = session.get(User, user_id)
        queued = evaluate_due_batches_for_user(session, user, queue, ref_utc=ref_wednesday)

    # Must queue exactly 1 batch (Batch 1) today for this purpose
    assert len(queued) == 1
    assert queued[0].id == b1_id
    assert queued[0].status == "QUEUED"

    # Verify job exists in queue
    claimed = queue.claim_batch(batch_size=10)
    assert len(claimed) == 1
    assert claimed[0].job_type == "send_batch"
    assert claimed[0].payload["batch_id"] == str(b1_id)

    # 2. Test Idempotency: Calling scheduler again immediately should queue NOTHING
    with session_factory() as session:
        user = session.get(User, user_id)
        second_run = evaluate_due_batches_for_user(session, user, queue, ref_utc=ref_wednesday)
        assert len(second_run) == 0


def test_api_tick_watchdog_endpoint():
    """
    Tests that /api/v1/tick triggers scheduler evaluation and returns response schema.
    """
    client = TestClient(app)
    headers = {"X-Tick-Secret": settings.TICK_SECRET}

    response = client.post("/api/v1/tick?batch_size=5", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "batches_queued" in data
    assert "jobs_processed" in data
    assert isinstance(data["batches_queued"], int)
    assert isinstance(data["jobs_processed"], int)
