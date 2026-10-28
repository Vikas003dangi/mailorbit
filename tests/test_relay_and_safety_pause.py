from unittest.mock import MagicMock, patch
import uuid
import httpx
import pytest

from apps.api.config import settings
from apps.worker.apps_script_relay import (
    AppsScriptRelayClient,
    QuotaExceededError,
    RelayAuthError,
    RelayError,
)
from apps.worker.dispatcher import dispatch_batch
from apps.worker.pacer import Pacer
from packages.shared.crypto import EncryptionService, EnvKeyManager
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Batch, Contact, Purpose, SenderRelay, User


def create_test_user_and_purpose(session):
    user = User(
        email=f"relay_tester_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="mock_hash",
    )
    session.add(user)
    session.flush()

    purpose = Purpose(
        user_id=user.id,
        name="Tech Exec Outreach",
        default_subject_template="Quick note for {company}",
        default_body_template="Hi {name}, admire your work at {company}.",
    )
    session.add(purpose)
    session.flush()

    return user, purpose


def test_apps_script_relay_client_success():
    """Verify AppsScriptRelayClient handles successful dispatch and returns quota."""
    client = AppsScriptRelayClient(
        script_url="https://script.google.com/macros/s/AKfycbytest/exec",
        auth_token="secret_token_123",
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "message": "Email dispatched successfully",
        "remaining_quota": 85,
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = client.send_email(
            from_email="user@gmail.com",
            to_email="lead@company.com",
            subject="Partnership",
            body_text="Hello!",
        )

        assert res["status"] == "SENT"
        assert res["remaining_quota"] == 85
        assert res["recipient"] == "lead@company.com"
        mock_post.assert_called_once()


def test_apps_script_relay_client_quota_exceeded():
    """Verify AppsScriptRelayClient raises QuotaExceededError on HTTP 429."""
    client = AppsScriptRelayClient(
        script_url="https://script.google.com/macros/s/AKfycbytest/exec",
        auth_token="secret_token_123",
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.json.return_value = {
        "success": False,
        "error": "QUOTA_EXCEEDED",
        "message": "Gmail daily sending quota has been reached",
    }

    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(QuotaExceededError) as exc_info:
            client.send_email(
                from_email="user@gmail.com",
                to_email="lead@company.com",
                subject="Partnership",
                body_text="Hello!",
            )
        assert "quota" in str(exc_info.value).lower()


def test_apps_script_relay_client_auth_error():
    """Verify AppsScriptRelayClient raises RelayAuthError on HTTP 401."""
    client = AppsScriptRelayClient(
        script_url="https://script.google.com/macros/s/AKfycbytest/exec",
        auth_token="bad_token",
    )

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "success": False,
        "error": "UNAUTHORIZED",
        "message": "Invalid relay token",
    }

    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(RelayAuthError):
            client.send_email(
                from_email="user@gmail.com",
                to_email="lead@company.com",
                subject="Partnership",
                body_text="Hello!",
            )


def test_10_percent_batch_safety_pause_circuit_breaker():
    """
    TRD Milestone M5 Core Acceptance Test:
    - 10% Batch Safety Pause Circuit Breaker:
      If failures or bounces exceed 10% in an active batch (after min 5 leads),
      the dispatch loop must IMMEDIATELY HALT and set batch.status = 'PAUSED'.
    """
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        user, purpose = create_test_user_and_purpose(session)

        # Create batch of 10 leads
        batch = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="High Risk Batch",
            size=10,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        # Add 10 leads: leads 2 and 4 have invalid/prohibited domains
        # (2 failures out of 5 evaluated = 40% failure rate > 10% threshold!)
        contacts = []
        for i in range(1, 11):
            if i in (2, 4):
                email = f"bad_lead_{i}@nodomain.com"  # Fails pre-send verification
            else:
                email = f"good_lead_{i}@verifiedtech.com"
            c = Contact(
                user_id=user.id,
                purpose_id=purpose.id,
                batch_id=batch.id,
                email=email,
                name=f"Lead {i}",
                company="TechCorp",
            )
            contacts.append(c)

        session.add_all(contacts)
        session.commit()
        batch_id = batch.id

    mock_sender = MagicMock()
    mock_sender.send_email.return_value = {"status": "SENT", "remaining_quota": 90}
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    # Dispatch batch with min_samples_for_safety=5
    with session_factory() as session:
        result = dispatch_batch(
            session=session,
            batch_id=batch_id,
            sender=mock_sender,
            pacer=test_pacer,
            min_samples_for_safety=5,
        )

    # Verify circuit breaker triggered!
    assert result["batch_status"] == "PAUSED"
    assert "Safety pause triggered" in result["paused_reason"]
    assert "10% threshold" in result["paused_reason"]

    # Verify database state
    with session_factory() as session:
        b = session.get(Batch, batch_id)
        assert b.status == "PAUSED"
        assert b.paused_reason is not None

        # Verify not all 10 leads were sent — processing was halted early!
        sent_count = session.query(Contact).filter(Contact.batch_id == batch_id, Contact.status == "SENT").count()
        assert sent_count < 8  # Stopped early to protect domain reputation!


def test_relay_quota_exhaustion_pauses_batch():
    """Verify that when a relay reports quota exhaustion, the batch pauses cleanly."""
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        user, purpose = create_test_user_and_purpose(session)

        batch = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="Quota Test Batch",
            size=2,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        c1 = Contact(user_id=user.id, purpose_id=purpose.id, batch_id=batch.id, email="lead1@tech.com", name="L1", company="C1")
        c2 = Contact(user_id=user.id, purpose_id=purpose.id, batch_id=batch.id, email="lead2@tech.com", name="L2", company="C2")
        session.add_all([c1, c2])
        session.commit()
        batch_id = batch.id

    # Sender raises QuotaExceededError
    mock_sender = MagicMock()
    mock_sender.send_email.side_effect = QuotaExceededError("Daily Gmail sending quota reached")
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    with session_factory() as session:
        result = dispatch_batch(
            session=session,
            batch_id=batch_id,
            sender=mock_sender,
            pacer=test_pacer,
        )

    assert result["batch_status"] == "PAUSED"
    assert "quota" in result["paused_reason"].lower()

    with session_factory() as session:
        b = session.get(Batch, batch_id)
        assert b.status == "PAUSED"

