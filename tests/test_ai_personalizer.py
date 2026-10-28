from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import uuid
import httpx
import pytest

from apps.api.config import settings
from apps.worker.ai_personalizer import GeminiPersonalizer, generate_email_content
from apps.worker.dispatcher import dispatch_batch
from apps.worker.pacer import Pacer
from packages.shared.auth import hash_password
from packages.shared.crypto import EncryptionService, EnvKeyManager
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import AIKey, Batch, Contact, Profile, Purpose, User


def create_test_setup(session):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"ai_user_{unique}@example.com",
        password_hash=hash_password("Secret123!"),
        timezone="UTC",
        is_active=True,
    )
    session.add(user)
    session.flush()

    profile = Profile(
        user_id=user.id,
        full_name="Alex Outreach",
    )
    session.add(profile)

    purpose = Purpose(
        user_id=user.id,
        name="Software Engineer Hiring",
        default_subject_template="Engineering role for {name} at {company}",
        default_body_template="Hi {name},\n\nWould love to discuss engineering opportunities at {company}.",
        is_active=True,
    )
    session.add(purpose)
    session.flush()

    contact = Contact(
        user_id=user.id,
        purpose_id=purpose.id,
        email="lead.alice@innovate.example.com",
        name="Alice Walker",
        company="Innovate AI",
        role="VP of Engineering",
    )
    session.add(contact)
    session.commit()
    return user, profile, purpose, contact


def test_gemini_personalizer_success():
    """Tests successful Gemini API JSON response parsing."""
    personalizer = GeminiPersonalizer(api_key="mock_gemini_api_key")

    mock_resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "subject": "Innovate AI Engineering Scale",
                                "body_text": "Hi Alice, saw Innovate AI's recent milestones in AI inference. Would love to connect regarding your engineering goals.",
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_json

    with patch("httpx.Client.post", return_value=mock_resp):
        contact = Contact(name="Alice", company="Innovate AI", role="VP Eng")
        result = personalizer.personalize(contact=contact)

    assert result is not None
    assert result["subject"] == "Innovate AI Engineering Scale"
    assert "Innovate AI's recent milestones" in result["body_text"]


def test_gemini_personalizer_rate_limit_and_template_fallback():
    """
    TRD Milestone M7 Core Acceptance Test:
    When Gemini returns HTTP 429 (rate limit), the personalizer must gracefully
    fall back to template interpolation without raising any errors.
    """
    personalizer = GeminiPersonalizer(api_key="mock_gemini_api_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {"error": "Quota exceeded"}

    contact = Contact(name="Bob", company="Starlight Labs", role="Founder")
    purpose = Purpose(
        default_subject_template="Question for {name} at {company}",
        default_body_template="Hi {name}, admire your leadership at {company}.",
    )

    with patch("httpx.Client.post", return_value=mock_resp):
        subject, body, is_ai = generate_email_content(
            contact=contact,
            purpose=purpose,
            personalizer=personalizer,
        )

    # Must successfully fall back to template!
    assert is_ai is False
    assert subject == "Question for Bob at Starlight Labs"
    assert body == "Hi Bob, admire your leadership at Starlight Labs."


def test_template_fallback_when_no_ai_key_configured():
    """Tests that emails render cleanly with templates when no AI key is present."""
    contact = Contact(name="Carol", company="Acme Corp", role="Lead Engineer")
    purpose = Purpose(
        default_subject_template="Quick note for {company}",
        default_body_template="Hi {name}, connecting with {company}.",
    )

    subject, body, is_ai = generate_email_content(
        contact=contact,
        purpose=purpose,
        personalizer=None,
    )

    assert is_ai is False
    assert subject == "Quick note for Acme Corp"
    assert body == "Hi Carol, connecting with Acme Corp."


def test_dispatch_batch_with_ai_personalization_integration():
    """
    End-to-end integration test:
    - User has encrypted AI key in database.
    - Dispatcher decrypts key and invokes GeminiPersonalizer.
    - Successfully delivers personalized email to mock sender.
    """
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)

    crypto = EncryptionService(EnvKeyManager(settings.ENCRYPTION_MASTER_KEY))

    with session_factory() as session:
        user, profile, purpose, contact = create_test_setup(session)

        # Add active AI key
        ai_key = AIKey(
            user_id=user.id,
            provider="gemini",
            api_key_ciphertext=crypto.encrypt("gemini_live_test_key_123"),
            model="gemini-2.5-flash",
            status="ACTIVE",
        )
        session.add(ai_key)

        # Create batch
        batch = Batch(
            user_id=user.id,
            purpose_id=purpose.id,
            name="AI Powered Batch",
            size=1,
            status="PENDING",
        )
        session.add(batch)
        session.flush()

        contact.batch_id = batch.id
        session.commit()
        batch_id = batch.id

    mock_resp_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "subject": "Tailored Outreach for Innovate AI",
                                "body_text": "Hello Alice Walker, reaching out regarding your VP of Engineering leadership at Innovate AI.",
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_resp_json

    mock_sender = MagicMock()
    mock_sender.send_email.return_value = {"status": "SENT"}
    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    with patch("httpx.Client.post", return_value=mock_resp):
        with session_factory() as session:
            result = dispatch_batch(
                session=session,
                batch_id=batch_id,
                sender=mock_sender,
                pacer=test_pacer,
            )

    assert result["sent_count"] == 1
    assert result["batch_status"] == "COMPLETED"

    # Verify mock sender received personalized email!
    mock_sender.send_email.assert_called_once()
    call_kwargs = mock_sender.send_email.call_args.kwargs
    assert call_kwargs["to_email"] == "lead.alice@innovate.example.com"
    assert call_kwargs["subject"] == "Tailored Outreach for Innovate AI"
    assert "VP of Engineering leadership at Innovate AI" in call_kwargs["body_text"]

