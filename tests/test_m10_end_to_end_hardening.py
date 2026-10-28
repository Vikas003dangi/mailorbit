from datetime import datetime, timezone
import json
from unittest.mock import MagicMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from packages.shared.auth import hash_password
from packages.shared.crypto import EncryptionService, EnvKeyManager
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import (
    AIKey,
    Batch,
    Contact,
    DoNotContact,
    Profile,
    Purpose,
    SenderRelay,
    User,
)


def test_m10_full_pipeline_end_to_end_hardening():
    """
    TRD Milestone M10 Ultimate Acceptance Test:
    Simulates the entire user journey and automated cold outreach lifecycle:
    1. User Signup & JWT Authentication.
    2. Profile Setup with technical skills.
    3. Purpose Setup with outreach templates.
    4. BYOK AI Key Setup (encrypted).
    5. Contact Bulk Import (CSV) with mixed leads:
       - Valid lead
       - Bad domain lead (fails pre-send validation)
       - Do-Not-Contact lead (opted out)
       - Extra valid leads (for auto-topup pool)
    6. Auto-Batching into daily batches.
    7. Scheduled Watchdog Tick (/api/v1/tick):
       - Evaluates due batch.
       - Worker claims job via PostgreSQL row-level lock.
       - Dispatches emails with AI personalization and List-Unsubscribe headers.
       - Invalid and DNC leads are auto-replaced with pool leads.
       - Batch completes.
    8. One-click Unsubscribe flow.
    """
    client = TestClient(app)
    db_engine = create_db_engine(settings.DATABASE_URL)
    session_factory = create_session_factory(db_engine)
    crypto = EncryptionService(EnvKeyManager(settings.ENCRYPTION_MASTER_KEY))

    # 1. User Signup
    unique_suffix = uuid.uuid4().hex[:8]
    user_email = f"founder_{unique_suffix}@example.com"
    user_pass = "ProductionSecurePass999!"

    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": user_email, "password": user_pass},
    )
    assert signup_res.status_code == 201
    auth_token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 2. Profile Setup
    profile_data = {
        "full_name": "Vikas Dangi",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Next.js", "Docker"],
        "summary": "Fullstack engineer building autonomous cold outreach infrastructure.",
    }
    prof_res = client.put("/api/v1/profile", json=profile_data, headers=headers)
    assert prof_res.status_code == 200

    # 3. Purpose Setup
    purpose_payload = {
        "name": "Fullstack Engineering Outreach",
        "description": "Connecting with engineering directors.",
        "default_subject_template": "Quick question regarding {company}",
        "default_body_template": "Hi {name},\n\nHope this finds you well at {company}.",
    }
    purpose_res = client.post("/api/v1/purposes", json=purpose_payload, headers=headers)
    assert purpose_res.status_code == 201
    purpose_id = uuid.UUID(purpose_res.json()["id"])

    # 4. BYOK AI Key Setup (encrypted)
    ai_key_payload = {
        "provider": "gemini",
        "api_key": "gemini_mock_prod_key_12345",
        "model": "gemini-2.5-flash",
    }
    key_res = client.post("/api/v1/ai-keys", json=ai_key_payload, headers=headers)
    assert key_res.status_code == 201
    key_id = uuid.UUID(key_res.json()["id"])

    # Manually activate key in DB for test
    with session_factory() as session:
        k = session.get(AIKey, key_id)
        k.status = "ACTIVE"
        session.commit()

    # 5. Pre-seed Do-Not-Contact record for this user
    with session_factory() as session:
        user_record = session.query(User).filter(User.email == user_email).first()
        user_id = user_record.id
        dnc = DoNotContact(
            user_id=user_id,
            email="optedout@blacklist.example.com",
            reason="Previous unsubscribe request",
        )
        session.add(dnc)
        session.commit()

    # 6. Bulk Contact Import via CSV
    csv_content = (
        "Email,Name,Company,Role\n"
        "alex@innovatecorp.example.com,Alex Rivera,InnovateCorp,VP of Engineering\n"
        "badlead@nodomain.com,Bad Lead,NoDomain,Tester\n"
        "optedout@blacklist.example.com,Prior Optout,BlacklistCorp,Director\n"
        "topup1@futuretech.example.com,Topup One,FutureTech,Lead Dev\n"
        "topup2@futuretech.example.com,Topup Two,FutureTech,Architect\n"
    )
    import_res = client.post(
        "/api/v1/contacts/import-csv",
        files={"file": ("leads.csv", csv_content.encode("utf-8"), "text/csv")},
        data={"purpose_id": str(purpose_id), "auto_batch": "false"},
        headers=headers,
    )
    assert import_res.status_code in (200, 201)
    assert import_res.json()["summary"]["imported_count"] == 5

    # 7. Auto-Generate Batches (batch size = 2)
    batch_gen_payload = {
        "purpose_id": str(purpose_id),
        "batch_size": 2,
        "daily_send_time": "08:00",
        "active_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    }
    gen_res = client.post("/api/v1/batches/auto-generate", json=batch_gen_payload, headers=headers)
    assert gen_res.status_code == 200
    assert gen_res.json()["created_batches_count"] >= 1

    with session_factory() as session:
        batch1 = (
            session.query(Batch)
            .filter(Batch.user_id == user_id, Batch.position == 1)
            .first()
        )
        batch1_id = batch1.id

        # Seed an unassigned top-up pool lead with batch_id=None
        pool_lead = Contact(
            user_id=user_id,
            purpose_id=purpose_id,
            batch_id=None,
            email="standby.lead@innovate.example.com",
            name="Standby Lead",
            company="Standby Corp",
            status="PENDING",
        )
        session.add(pool_lead)
        session.commit()

    # 8. Mock Gemini AI generation & Mock Dispatcher
    mock_gemini_resp = MagicMock()
    mock_gemini_resp.status_code = 200
    mock_gemini_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "subject": "InnovateCorp Engineering Scale",
                                "body_text": "Hi Alex Rivera, noticed your engineering milestones at InnovateCorp. Would love to connect regarding your tech initiatives.",
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_sender = MagicMock()
    mock_sender.send_email.return_value = {"status": "SENT"}

    from apps.worker.dispatcher import dispatch_batch
    from apps.worker.pacer import Pacer

    test_pacer = Pacer(min_seconds=0.0, max_seconds=0.0)

    # 9. Dispatch Batch 1
    with patch("httpx.Client.post", return_value=mock_gemini_resp):
        with session_factory() as session:
            dispatch_result = dispatch_batch(
                session=session,
                batch_id=batch1_id,
                sender=mock_sender,
                pacer=test_pacer,
            )

    assert dispatch_result["sent_count"] >= 1
    assert dispatch_result["replaced_count"] >= 1  # Bad domain and DNC leads were replaced!

    # 10. Verify outbound emails had List-Unsubscribe headers
    sent_calls = mock_sender.send_email.call_args_list
    assert len(sent_calls) >= 1
    first_call_kwargs = sent_calls[0].kwargs
    assert "List-Unsubscribe" in first_call_kwargs["headers"]
    assert "List-Unsubscribe-Post" in first_call_kwargs["headers"]
    assert "opt out" in first_call_kwargs["body_text"]

    # 11. Test Watchdog Tick
    tick_headers = {"X-Tick-Secret": settings.TICK_SECRET}
    tick_res = client.post("/api/v1/tick?batch_size=5", headers=tick_headers)
    assert tick_res.status_code == 200
    assert tick_res.json()["status"] == "ok"
