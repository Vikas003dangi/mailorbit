"""
Milestone 2 Campaign Engine Core Test Suite.
Tests:
- Water-filling fair-share balancing algorithm (all worked mathematical examples).
- Direct paste lead ingestion (commas, newlines, semicolons, named tokens).
- Move contacts between batches endpoint.
- Calendar start_date, stop_date, and skip_dates filtering.
- Not Working quarantine and ContactReplacement audit log.
- Auto-balance endpoint.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from apps.api.services.contact_importer import parse_paste_text
from apps.worker.dispatcher import dispatch_batch
from apps.worker.pacer import Pacer
from apps.worker.scheduler import (
    evaluate_due_batches_for_user,
    get_user_local_datetime,
    is_purpose_date_active,
)
from apps.worker.water_filler import SubBatchLike, water_fill_fair_share
from packages.shared.auth import create_access_token, hash_password
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Batch, Contact, ContactReplacement, Purpose, SenderRelay, User

client = TestClient(app)


def test_water_fill_all_worked_examples():
    """Verifies all worked mathematical examples from M2_CAMPAIGN_ENGINE_DESIGN.md."""
    # Example 1: 3 sub-batches (30 each), budget 30 -> 10, 10, 10
    sb1 = SubBatchLike(id="sb1", pending_count=30)
    sb2 = SubBatchLike(id="sb2", pending_count=30)
    sb3 = SubBatchLike(id="sb3", pending_count=30)
    res1 = water_fill_fair_share([sb1, sb2, sb3], daily_budget=30)
    assert res1 == {"sb1": 10, "sb2": 10, "sb3": 10}
    assert sum(res1.values()) == 30

    # Example 2: 4 sub-batches (20 each), budget 30 -> 8, 8, 7, 7
    a1 = SubBatchLike(id="a1", pending_count=20)
    a2 = SubBatchLike(id="a2", pending_count=20)
    b1 = SubBatchLike(id="b1", pending_count=20)
    b2 = SubBatchLike(id="b2", pending_count=20)
    res2 = water_fill_fair_share([a1, a2, b1, b2], daily_budget=30)
    assert res2 == {"a1": 8, "a2": 8, "b1": 7, "b2": 7}
    assert sum(res2.values()) == 30

    # Example 3: 2 sub-batches (10 pending each), budget 30 -> 10, 10 (20 total, 10 unused)
    s1 = SubBatchLike(id="s1", pending_count=10)
    s2 = SubBatchLike(id="s2", pending_count=10)
    res3 = water_fill_fair_share([s1, s2], daily_budget=30)
    assert res3 == {"s1": 10, "s2": 10}
    assert sum(res3.values()) == 20

    # Example 4: Asymmetric (sub-batch 1 has 4, sub-batch 2 has 30), budget 30 -> 4, 26 (30 total)
    asym1 = SubBatchLike(id="asym1", pending_count=4)
    asym2 = SubBatchLike(id="asym2", pending_count=30)
    res4 = water_fill_fair_share([asym1, asym2], daily_budget=30)
    assert res4 == {"asym1": 4, "asym2": 26}
    assert sum(res4.values()) == 30

    # Edge Case: 0 budget -> 0 allocated
    res5 = water_fill_fair_share([sb1, sb2], daily_budget=0)
    assert res5 == {"sb1": 0, "sb2": 0}


def test_paste_email_importer_various_formats():
    """Verifies that unstructured pasted emails are normalized cleanly."""
    raw_text = (
        "alice@company.com, bob@startup.io;\n"
        "John Doe <john@engineer.org>\n"
        "recruiter@tech.co\r\n"
        "Jane Smith: jane@design.net\n"
        "invalid-email-ignored\n"
        "ceo@venture.com, "
    )
    rows = parse_paste_text(raw_text)
    emails = [r["email"] for r in rows]
    names = {r["email"]: r["name"] for r in rows}

    assert "alice@company.com" in emails
    assert "bob@startup.io" in emails
    assert "john@engineer.org" in emails
    assert names["john@engineer.org"] == "John Doe"
    assert "recruiter@tech.co" in emails
    assert "jane@design.net" in emails
    assert "ceo@venture.com" in emails
    assert "invalid-email-ignored" not in emails


def test_paste_contacts_api_endpoint():
    """Verifies POST /api/v1/contacts/paste creates contacts and auto-batches."""
    engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    unique = uuid.uuid4().hex[:6]
    user_email = f"paste_tester_{unique}@example.com"

    with session_factory() as session:
        user = User(email=user_email, password_hash=hash_password("Pass123!"))
        session.add(user)
        session.commit()
        user_id = user.id

    token = create_access_token(
        user_id=str(user_id),
        email=user_email,
        secret_key=settings.TICK_SECRET,
    )
    headers = {"Authorization": f"Bearer {token}"}

    paste_payload = {
        "raw_text": "dev1@test.com, dev2@test.com\nAlice <dev3@test.com>",
        "auto_batch": True,
        "batch_size": 2,
    }

    res = client.post("/api/v1/contacts/paste", json=paste_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["summary"]["imported_count"] == 3
    assert data["created_batches_count"] >= 1


def test_move_contacts_between_batches():
    """Verifies POST /api/v1/batches/{batch_id}/move-contacts reassigns leads."""
    engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    unique = uuid.uuid4().hex[:6]
    user_email = f"move_tester_{unique}@example.com"
    with session_factory() as session:
        user = User(email=user_email, password_hash=hash_password("Pass123!"))
        session.add(user)
        session.flush()

        batch_a = Batch(user_id=user.id, name="Batch A", size=10)
        batch_b = Batch(user_id=user.id, name="Batch B", size=10)
        session.add_all([batch_a, batch_b])
        session.flush()

        c1 = Contact(user_id=user.id, batch_id=batch_a.id, email=f"c1_{unique}@test.com")
        c2 = Contact(user_id=user.id, batch_id=batch_a.id, email=f"c2_{unique}@test.com")
        session.add_all([c1, c2])
        session.commit()

        user_id = user.id
        batch_b_id = batch_b.id
        c1_id = c1.id
        c2_id = c2.id

    token = create_access_token(
        user_id=str(user_id),
        email=user_email,
        secret_key=settings.TICK_SECRET,
    )
    headers = {"Authorization": f"Bearer {token}"}

    move_payload = {"contact_ids": [str(c1_id), str(c2_id)]}
    res = client.post(f"/api/v1/batches/{batch_b_id}/move-contacts", json=move_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["moved_count"] == 2

    with session_factory() as session:
        updated_c1 = session.query(Contact).filter(Contact.id == c1_id).first()
        assert updated_c1.batch_id == batch_b_id


def test_calendar_date_filters_and_skip_dates():
    """Verifies that start_date, stop_date, and skip_dates are strictly honored by the scheduler."""
    ref_now = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
    today = ref_now.date()

    # Case 1: Start date in future -> inactive
    future_purpose = Purpose(
        name="Future Launch",
        start_date=today + timedelta(days=2),
    )
    assert is_purpose_date_active(future_purpose, ref_now) is False

    # Case 2: Stop date in past -> inactive
    expired_purpose = Purpose(
        name="Expired Campaign",
        stop_date=today - timedelta(days=1),
    )
    assert is_purpose_date_active(expired_purpose, ref_now) is False

    # Case 3: Today is in skip_dates -> inactive
    holiday_purpose = Purpose(
        name="Holiday Skip",
        skip_dates=[today.strftime("%Y-%m-%d")],
    )
    assert is_purpose_date_active(holiday_purpose, ref_now) is False

    # Case 4: Valid date window -> active
    active_purpose = Purpose(
        name="Active Window",
        start_date=today - timedelta(days=1),
        stop_date=today + timedelta(days=5),
        skip_dates=["2026-12-25"],
    )
    assert is_purpose_date_active(active_purpose, ref_now) is True


def test_not_working_quarantine_and_audit_trail():
    """Verifies that pre-send failures quarantine leads to Not Working and write to ContactReplacement."""
    engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    unique = uuid.uuid4().hex[:6]
    user_email = f"quarantine_{unique}@example.com"
    with session_factory() as session:
        user = User(email=user_email, password_hash=hash_password("Pass123!"))
        session.add(user)
        session.flush()

        purpose = Purpose(user_id=user.id, name="Test Purpose")
        session.add(purpose)
        session.flush()

        batch = Batch(user_id=user.id, purpose_id=purpose.id, name="Test Batch", size=2)
        session.add(batch)
        session.flush()

        # Contact 1: invalid domain (will fail verification)
        bad_lead = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            batch_id=batch.id,
            email=f"bad_lead_{unique}@nodomain.com",
            name="Bad Lead",
        )
        # Contact 2: clean replacement in pool
        clean_lead = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            batch_id=None,
            email=f"clean_lead_{unique}@verifiedtech.com",
            name="Clean Lead",
        )
        session.add_all([bad_lead, clean_lead])
        session.commit()

        user_id = user.id
        batch_id = batch.id
        bad_lead_id = bad_lead.id
        clean_lead_id = clean_lead.id

    mock_sender = MagicMock()
    mock_sender.send_email.return_value = {"status": "SENT"}
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    with patch("apps.worker.dispatcher.verify_email_domain") as mock_dns:
        mock_dns.side_effect = lambda email: (False, "NXDOMAIN") if "nodomain.com" in email else (True, None)
        with session_factory() as session:
            result = dispatch_batch(session=session, batch_id=batch_id, sender=mock_sender, pacer=test_pacer)

    assert result["replaced_count"] == 1
    assert result["sent_count"] == 1

    # Verify Not Working endpoint and Replacements audit log via API
    token = create_access_token(
        user_id=str(user_id),
        email=user_email,
        secret_key=settings.TICK_SECRET,
    )
    headers = {"Authorization": f"Bearer {token}"}

    not_working_res = client.get("/api/v1/contacts/not-working", headers=headers)
    assert not_working_res.status_code == 200
    nw_data = not_working_res.json()
    assert len(nw_data) >= 1
    assert nw_data[0]["id"] == str(bad_lead_id)

    rep_res = client.get("/api/v1/contacts/replacements", headers=headers)
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert len(rep_data) >= 1
    assert rep_data[0]["original_contact_id"] == str(bad_lead_id)
    assert rep_data[0]["replaced_by_contact_id"] == str(clean_lead_id)


def test_auto_balance_endpoint():
    """Verifies POST /api/v1/batches/auto-balance calculates water-fill allocations."""
    engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(engine)

    unique = uuid.uuid4().hex[:6]
    user_email = f"autobalance_{unique}@example.com"
    with session_factory() as session:
        user = User(email=user_email, password_hash=hash_password("Pass123!"))
        session.add(user)
        session.flush()

        # Create 2 batches: one with 4 leads, one with 30 leads
        b1 = Batch(user_id=user.id, name="Small Batch", size=4)
        b2 = Batch(user_id=user.id, name="Big Batch", size=30)
        session.add_all([b1, b2])
        session.flush()

        contacts = []
        for i in range(4):
            contacts.append(Contact(user_id=user.id, batch_id=b1.id, email=f"small_{i}_{unique}@test.com"))
        for i in range(30):
            contacts.append(Contact(user_id=user.id, batch_id=b2.id, email=f"big_{i}_{unique}@test.com"))
        session.add_all(contacts)
        session.commit()

        user_id = user.id
        b1_id = str(b1.id)
        b2_id = str(b2.id)

    token = create_access_token(
        user_id=str(user_id),
        email=user_email,
        secret_key=settings.TICK_SECRET,
    )
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/batches/auto-balance?daily_budget=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["daily_budget"] == 30
    assert data["total_pending"] == 34
    assert data["allocations"][b1_id] == 4
    assert data["allocations"][b2_id] == 26
    assert data["estimated_days"] == 2
