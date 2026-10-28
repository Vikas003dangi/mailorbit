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
