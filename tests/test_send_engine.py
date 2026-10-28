from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from apps.worker.dispatcher import dispatch_batch, verify_email_domain
from apps.worker.pacer import Pacer
from apps.worker.postgres_queue import PostgresJobQueue
from apps.worker.sender import LocalMailpitSender
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Batch, Contact, JobModel, Purpose, User

client = TestClient(app)


def get_authenticated_user_and_headers():
    email = f"sender_test_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    user_id = res.json()["user"]["id"]
    return uuid.UUID(user_id), {"Authorization": f"Bearer {token}"}


def test_pre_send_email_verification():
    """Verify that domain syntax and prohibited TLDs are rejected pre-send."""
    assert verify_email_domain("recruiter@stripe.com")[0] is True
    assert verify_email_domain("talent@google.co.uk")[0] is True

    # Bad format
    assert verify_email_domain("invalid-no-at-sign")[0] is False
    assert verify_email_domain("@nodomain.com")[0] is False

    # Prohibited / unreachable domains
    is_valid, reason = verify_email_domain("bad_lead@nodomain.com")
    assert is_valid is False
    assert "unreachable domain" in reason


def test_postgres_job_queue_row_level_leasing():
    """
    TRD Milestone M4 Acceptance Test:
    - Enqueue jobs
    - Claim batch with lease
    - Verify atomic locking (no duplicate claiming)
    - Mark complete
    """
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)
    pq = PostgresJobQueue(session_factory=session_factory)

    job_payload = {"test_marker": uuid.uuid4().hex}
    job = pq.enqueue("test_job", job_payload, max_attempts=2)
    assert job.status == "PENDING"
    assert job.job_type == "test_job"

    # Worker 1 claims the job
    claimed_1 = pq.claim_batch(batch_size=10, lease_seconds=30)
    matching_1 = [j for j in claimed_1 if j.id == job.id]
    assert len(matching_1) == 1
    assert matching_1[0].status == "RUNNING"
    assert matching_1[0].lease_id is not None

    # Worker 2 attempts to claim simultaneously — job is leased, must not be claimed again
    claimed_2 = pq.claim_batch(batch_size=10, lease_seconds=30)
    matching_2 = [j for j in claimed_2 if j.id == job.id]
    assert len(matching_2) == 0  # Atomic row lock: zero duplicate leasing!

    # Complete the job
    pq.complete(job.id)

    # Verify status in database
    with session_factory() as session:
        rec = session.get(JobModel, uuid.UUID(job.id))
        assert rec.status == "COMPLETED"
        assert rec.lease_id is None


def test_auto_topup_replacement_on_presend_failure():
    """
    TRD Milestone M4 Core Acceptance Test:
    - 2 valid leads + 1 bad domain lead in batch of 3
    - 2 unassigned pending leads available in pool
    - Dispatch batch:
        - Bad lead fails pre-send verification -> marked INACTIVE
        - Replacement lead automatically pulled from pending pool
        - Exactly 3 valid emails dispatched
        - Batch status transitions to COMPLETED
    """
    user_id, headers = get_authenticated_user_and_headers()
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        # 1. Create Purpose
        purpose = Purpose(
            user_id=user_id,
            name="Founding Engineer Outreach",
            default_subject_template="Quick question for {name} at {company}",
            default_body_template="Hi {name}, admire what {company} is doing.",
        )
        session.add(purpose)
        session.flush()

        # 2. Create Batch
        batch = Batch(
            user_id=user_id,
            purpose_id=purpose.id,
            name="Batch Alpha",
            size=3,
            position=1,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        # 3. Create 3 assigned contacts: 2 valid, 1 bad
        c1 = Contact(user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="alice@goodtech.com", name="Alice", company="GoodTech")
        c2 = Contact(user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="bob@nodomain.com", name="Bob", company="BadDomain")  # Will fail pre-send!
        c3 = Contact(user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="carol@techstar.com", name="Carol", company="TechStar")
        session.add_all([c1, c2, c3])

        # 4. Create 2 unassigned pending contacts for auto-topup
        topup1 = Contact(user_id=user_id, purpose_id=purpose.id, batch_id=None, email="topup_dave@nextcorp.com", name="Dave", company="NextCorp")
        topup2 = Contact(user_id=user_id, purpose_id=purpose.id, batch_id=None, email="topup_eva@future.com", name="Eva", company="Future")
        session.add_all([topup1, topup2])
        session.commit()

        batch_id = batch.id
        bob_id = c2.id
        topup1_id = topup1.id

    # Mock SMTP sender to intercept emails and verify receipt
    mock_sender = MagicMock(spec=LocalMailpitSender)
    mock_sender.send_email.return_value = {
        "status": "SENT",
        "message_id": "<simulated@mailorbit.local>",
        "recipient": "recipient@example.com",
    }
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    # 5. Execute batch dispatch
    with session_factory() as session:
        result = dispatch_batch(
            session=session,
            batch_id=batch_id,
            sender=mock_sender,
            pacer=test_pacer,
        )

    # 6. Verify dispatch results
    assert result["sent_count"] == 3  # Alice, Carol, and Topup Dave!
    assert result["failed_count"] == 1  # Bob failed pre-send!
    assert result["replaced_count"] == 1  # 1 replacement was triggered!
    assert result["batch_status"] == "COMPLETED"

    # 7. Verify database states
    with session_factory() as session:
        # Bob is now INACTIVE with failure reason recorded
        bob = session.get(Contact, bob_id)
        assert bob.status == "INACTIVE"
        assert "Pre-send verification failed" in bob.status_reason

        # Topup Dave was claimed into this batch and marked SENT
        dave = session.get(Contact, topup1_id)
        assert dave.batch_id == batch_id
        assert dave.status == "SENT"
        assert dave.sent_at is not None

        # Alice and Carol marked SENT
        alice = session.query(Contact).filter(Contact.email == "alice@goodtech.com").first()
        assert alice.status == "SENT"


def test_batch_dispatch_endpoint_via_api():
    """Verify POST /api/v1/batches/{batch_id}/dispatch endpoint."""
    user_id, headers = get_authenticated_user_and_headers()
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        batch = Batch(
            user_id=user_id,
            name="Quick Batch",
            size=1,
            position=1,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        lead = Contact(
            user_id=user_id,
            batch_id=batch.id,
            email="founder@ycombinator.com",
            name="Sam",
            company="YC",
        )
        session.add(lead)
        session.commit()
        batch_id = str(batch.id)

    with patch("apps.worker.dispatcher.LocalMailpitSender.send_email") as mock_send:
        mock_send.return_value = {"status": "SENT", "message_id": "<test@local>"}
        res = client.post(f"/api/v1/batches/{batch_id}/dispatch", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["sent_count"] == 1
        assert data["batch_status"] == "COMPLETED"

