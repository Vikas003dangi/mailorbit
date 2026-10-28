from datetime import datetime
from unittest.mock import MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from apps.worker.dispatcher import dispatch_batch
from apps.worker.pacer import Pacer
from packages.shared.auth import hash_password
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Batch, Contact, DoNotContact, Purpose, User
from packages.shared.unsubscribe import (
    decode_unsubscribe_token,
    generate_unsubscribe_headers,
    generate_unsubscribe_token,
)


def create_test_entities(session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"dnc_user_{unique}@example.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
    )
    session.add(user)
    session.flush()

    purpose = Purpose(
        user_id=user.id,
        name="DNC Test Outreach",
        default_subject_template="Hello {name}",
        default_body_template="Testing DNC rules for {company}",
        is_active=True,
    )
    session.add(purpose)
    session.flush()
    return user, purpose


def test_unsubscribe_token_codec():
    user_id = uuid.uuid4()
    contact_id = uuid.uuid4()
    email = "lead.optout@example.com"

    token = generate_unsubscribe_token(
        user_id=user_id,
        contact_id=contact_id,
        email=email,
        secret_key=settings.ENCRYPTION_MASTER_KEY,
    )
    assert token is not None

    decoded = decode_unsubscribe_token(token, secret_key=settings.ENCRYPTION_MASTER_KEY)
    assert decoded["user_id"] == str(user_id)
    assert decoded["sub"] == str(contact_id)
    assert decoded["email"] == email


def test_unsubscribe_get_endpoint_marks_contact_and_creates_dnc_record():
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        user, purpose = create_test_entities(session)
        contact = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            email="victim@reachout.example.com",
            name="Victim Lead",
            company="Victim Corp",
            status="SENT",
        )
        session.add(contact)
        session.commit()
        user_id, contact_id = user.id, contact.id

    token = generate_unsubscribe_token(
        user_id=user_id,
        contact_id=contact_id,
        email="victim@reachout.example.com",
        secret_key=settings.ENCRYPTION_MASTER_KEY,
    )

    client = TestClient(app)
    response = client.get(f"/api/v1/unsubscribe?token={token}")
    assert response.status_code == 200
    assert "Unsubscribed" in response.text
    assert "victim@reachout.example.com" in response.text

    # Verify database records
    with session_factory() as session:
        dnc = (
            session.query(DoNotContact)
            .filter(DoNotContact.user_id == user_id, DoNotContact.email == "victim@reachout.example.com")
            .first()
        )
        assert dnc is not None
        assert dnc.reason == "Clicked email unsubscribe link"

        c = session.get(Contact, contact_id)
        assert c.status == "UNSUBSCRIBED"


def test_unsubscribe_post_rfc8058_one_click():
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        user, purpose = create_test_entities(session)
        contact = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            email="oneclick@reachout.example.com",
            name="OneClick Lead",
            status="SENT",
        )
        session.add(contact)
        session.commit()
        user_id, contact_id = user.id, contact.id

    token = generate_unsubscribe_token(
        user_id=user_id,
        contact_id=contact_id,
        email="oneclick@reachout.example.com",
        secret_key=settings.ENCRYPTION_MASTER_KEY,
    )

    client = TestClient(app)
    response = client.post(f"/api/v1/unsubscribe?token={token}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["email"] == "oneclick@reachout.example.com"

    # Verify idempotency
    repeat_res = client.post(f"/api/v1/unsubscribe?token={token}")
    assert repeat_res.status_code == 200


def test_pre_send_dnc_check_blocks_email_and_auto_topup_replaces():
    """
    TRD Milestone M9 Core Acceptance Test:
    - Pre-send checks DoNotContact table.
    - If contact is on DNC list, email is NEVER sent.
    - Contact is marked UNSUBSCRIBED.
    - An available pending contact is auto-topped up into the batch.
    """
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    with session_factory() as session:
        user, purpose = create_test_entities(session)

        # Pre-seed DNC record
        dnc = DoNotContact(
            user_id=user.id,
            email="blocked@donotcontact.example.com",
            reason="Prior opt-out",
        )
        session.add(dnc)

        batch = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="DNC Test Batch",
            size=1,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        # Contact 1: in DNC list (in batch)
        contact_blocked = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            batch_id=batch.id,
            email="blocked@donotcontact.example.com",
            name="Blocked Person",
            company="Blocked Inc",
        )
        # Contact 2: clean lead (unassigned top-up pool)
        contact_replacement = Contact(
            user_id=user.id,
            purpose_id=purpose.id,
            batch_id=None,
            email="clean.replacement@innovate.example.com",
            name="Clean Replacement",
            company="Innovate Inc",
        )
        session.add_all([contact_blocked, contact_replacement])
        session.commit()
        batch_id = batch.id
        replacement_id = contact_replacement.id
        blocked_id = contact_blocked.id

    mock_sender = MagicMock()
    mock_sender.send_email.return_value = {"status": "SENT"}
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    with session_factory() as session:
        result = dispatch_batch(
            session=session,
            batch_id=batch_id,
            sender=mock_sender,
            pacer=test_pacer,
        )

    # 1 replaced, 1 sent!
    assert result["replaced_count"] == 1
    assert result["sent_count"] == 1

    # Verify mock sender ONLY received clean replacement, NEVER blocked lead!
    mock_sender.send_email.assert_called_once()
    call_kwargs = mock_sender.send_email.call_args.kwargs
    assert call_kwargs["to_email"] == "clean.replacement@innovate.example.com"
    assert "List-Unsubscribe" in call_kwargs["headers"]
    assert "List-Unsubscribe-Post" in call_kwargs["headers"]
    assert "opt out" in call_kwargs["body_text"]

    # Verify database state
    with session_factory() as session:
        b = session.get(Contact, blocked_id)
        assert b.status == "UNSUBSCRIBED"
        assert "Do-Not-Contact list" in b.status_reason

        r = session.get(Contact, replacement_id)
        assert r.status == "SENT"
        assert r.batch_id == batch_id

