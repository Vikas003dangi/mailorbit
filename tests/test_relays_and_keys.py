import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.dependencies import SessionFactory, get_encryption_service
from apps.api.main import app
from packages.shared.schema import AIKey, SenderRelay

client = TestClient(app)


def test_secrets_encryption_and_zero_leakage():
    email = f"crypto_user_{uuid.uuid4().hex[:6]}@example.com"
    password = "CryptoPassword123!"

    # 1. Signup user
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # =========================================================================
    # SENDER RELAY TESTS
    # =========================================================================
    secret_relay_token = "mo_relay_super_secret_token_12345"
    relay_payload = {
        "email": "sender.vikas@gmail.com",
        "script_url": "https://script.google.com/macros/s/AKfycb_sample/exec",
        "auth_token": secret_relay_token,
        "daily_cap": 35,
    }

    # Save sender relay
    res = client.post("/api/v1/senders", json=relay_payload, headers=headers)
    assert res.status_code == 201
    relay_data = res.json()
    relay_id = relay_data["id"]

    # SECURITY CHECK: Plaintext secret must NEVER be returned in response
    assert secret_relay_token not in str(relay_data)
    # SECURITY CHECK: Raw ciphertext must NEVER be returned in response
    assert "v1:" not in str(relay_data)
    # Must provide masked representation (last 4 characters per TRD section 7)
    assert relay_data["masked_token"] == "••••••••2345"
    assert relay_data["has_token"] is True

    # Check database row directly
    db: Session = SessionFactory()
    try:
        db_relay = db.query(SenderRelay).filter(SenderRelay.id == relay_id).first()
        assert db_relay is not None
        # Must be encrypted with v1: AES-256-GCM format
        assert db_relay.auth_token_ciphertext.startswith("v1:")
        assert db_relay.auth_token_ciphertext != secret_relay_token

        # Verify backend decryptor recovers original secret
        crypto = get_encryption_service()
        assert crypto.decrypt(db_relay.auth_token_ciphertext) == secret_relay_token
    finally:
        db.close()

    # List relays
    list_res = client.get("/api/v1/senders", headers=headers)
    assert list_res.status_code == 200
    relays = list_res.json()
    assert len(relays) == 1
    assert secret_relay_token not in str(relays)
    assert "v1:" not in str(relays)
    assert relays[0]["masked_token"] == "••••••••2345"

    # =========================================================================
    # AI KEY TESTS
    # =========================================================================
    secret_gemini_key = "AIzaSyDummyGeminiKey_ABCDEF_9999"
    key_payload = {
        "provider": "gemini",
        "api_key": secret_gemini_key,
        "model": "gemini-2.5-flash",
    }

    # Save AI key
    key_res = client.post("/api/v1/ai-keys", json=key_payload, headers=headers)
    assert key_res.status_code == 201
    key_data = key_res.json()
    key_id = key_data["id"]

    # SECURITY CHECK: Plaintext key must NEVER be returned in response
    assert secret_gemini_key not in str(key_data)
    # SECURITY CHECK: Raw ciphertext must NEVER be returned in response
    assert "v1:" not in str(key_data)
    # Must provide masked representation (last 4 characters per TRD section 7)
    assert key_data["masked_key"] == "••••••••9999"
    assert key_data["has_key"] is True

    # Check database row directly
    db = SessionFactory()
    try:
        db_key = db.query(AIKey).filter(AIKey.id == key_id).first()
        assert db_key is not None
        assert db_key.api_key_ciphertext.startswith("v1:")
        assert db_key.api_key_ciphertext != secret_gemini_key

        # Verify backend decryptor recovers original key
        assert crypto.decrypt(db_key.api_key_ciphertext) == secret_gemini_key
    finally:
        db.close()

    # List AI keys
    keys_res = client.get("/api/v1/ai-keys", headers=headers)
    assert keys_res.status_code == 200
    keys = keys_res.json()
    assert len(keys) == 1
    assert secret_gemini_key not in str(keys)
    assert "v1:" not in str(keys)
    assert keys[0]["masked_key"] == "••••••••9999"

    # =========================================================================
    # DELETION & ZERO PERSISTENCE
    # =========================================================================
    del_relay = client.delete(f"/api/v1/senders/{relay_id}", headers=headers)
    assert del_relay.status_code == 204

    del_key = client.delete(f"/api/v1/ai-keys/{key_id}", headers=headers)
    assert del_key.status_code == 204

    # Verify completely deleted from DB
    db = SessionFactory()
    try:
        assert db.query(SenderRelay).filter(SenderRelay.id == relay_id).first() is None
        assert db.query(AIKey).filter(AIKey.id == key_id).first() is None
    finally:
        db.close()


def test_production_batch_without_relay_pauses_and_zero_contacts_sent(monkeypatch):
    """
    Verifies that in production mode, a batch without an active relay:
    1. Stops with 'Connect your sender' status.
    2. Never marks any contact as sent or delivered.
    """
    from apps.api.config import settings
    from apps.worker.dispatcher import dispatch_batch
    from packages.shared.schema import Batch, Contact, Purpose, User

    # Force production environment
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    db: Session = SessionFactory()
    try:
        user_id = uuid.uuid4()
        user = User(id=user_id, email=f"prod_sender_test_{uuid.uuid4().hex[:6]}@example.com", password_hash="dummy")
        purpose = Purpose(id=uuid.uuid4(), user_id=user_id, name="Eng Outreach")
        batch = Batch(id=uuid.uuid4(), user_id=user_id, purpose_id=purpose.id, name="Prod Batch", size=10, status="PENDING")
        c1 = Contact(id=uuid.uuid4(), user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="lead1@example.com", status="PENDING")
        c2 = Contact(id=uuid.uuid4(), user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="lead2@example.com", status="PENDING")
        db.add_all([user, purpose, batch, c1, c2])
        db.commit()

        # Execute dispatch
        res = dispatch_batch(session=db, batch_id=batch.id)

        assert res["status"] == "PAUSED"
        assert "Connect your sender" in res["paused_reason"]
        assert res["sent_count"] == 0

        # Check database records directly
        db.refresh(batch)
        db.refresh(c1)
        db.refresh(c2)

        assert batch.status == "PAUSED"
        assert "Connect your sender" in batch.paused_reason
        assert c1.status == "PENDING"
        assert c1.sent_at is None
        assert c2.status == "PENDING"
        assert c2.sent_at is None
    finally:
        db.close()


def test_contacts_never_marked_sent_without_real_relay_response():
    """
    Verifies that if a relay client encounters an error or fails to dispatch,
    contact status is never marked SENT or DELIVERED.
    """
    from apps.worker.dispatcher import dispatch_batch
    from apps.worker.apps_script_relay import RelayError
    from packages.shared.schema import Batch, Contact, Purpose, User

    class MockFailingRelay:
        def send_email(self, *args, **kwargs):
            raise RelayError("Simulated Apps Script 500 error from Google servers")

    db: Session = SessionFactory()
    try:
        user_id = uuid.uuid4()
        user = User(id=user_id, email=f"failing_relay_{uuid.uuid4().hex[:6]}@example.com", password_hash="dummy")
        purpose = Purpose(id=uuid.uuid4(), user_id=user_id, name="Test Outreach")
        batch = Batch(id=uuid.uuid4(), user_id=user_id, purpose_id=purpose.id, name="Failing Batch", size=10, status="PENDING")
        contact = Contact(id=uuid.uuid4(), user_id=user_id, purpose_id=purpose.id, batch_id=batch.id, email="lead@reliabledomain.com", status="PENDING")
        db.add_all([user, purpose, batch, contact])
        db.commit()

        # Run dispatch with explicit failing sender
        res = dispatch_batch(session=db, batch_id=batch.id, sender=MockFailingRelay())

        assert res["sent_count"] == 0
        db.refresh(contact)
        # Contact must NOT be marked SENT
        assert contact.status != "SENT"
        assert contact.status != "DELIVERED"
        assert contact.sent_at is None
        assert contact.status == "FAILED"
        assert "Simulated Apps Script 500 error" in contact.error
    finally:
        db.close()
