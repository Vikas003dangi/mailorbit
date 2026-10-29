import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.schema import AIKey, Purpose, SenderRelay

client = TestClient(app)


def get_auth_token():
    email = f"copilot_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post("/api/v1/auth/signup", json={"email": email, "password": "SecurePassword123!"})
    assert res.status_code == 201
    return res.json()["access_token"], email


def test_ai_draft_fallback_template():
    token, _ = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Set profile
    client.put("/api/v1/profile", json={
        "full_name": "Vikas Dangi",
        "headline": "Lead AI Engineer",
        "skills": ["python", "fastapi", "react", "machine learning"]
    }, headers=headers)

    # Request draft without BYOK key (should fallback to intelligent template with matched skills)
    draft_res = client.post("/api/v1/ai/draft", json={
        "recipient_name": "Sarah",
        "recipient_company": "Stripe",
        "recipient_role": "Senior Backend Engineer",
        "job_description": "Looking for a Python and FastAPI expert with machine learning experience to scale backend APIs."
    }, headers=headers)

    assert draft_res.status_code == 200
    data = draft_res.json()
    assert "Stripe" in data["subject"]
    assert "Sarah" in data["body_text"]
    assert "Vikas Dangi" in data["body_text"]
    assert "python" in data["matched_skills"]
    assert data["match_score"] > 0
    assert data["provider"] == "template"


def test_quick_send_direct_dispatch():
    token, email = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Add sender relay
    relay_res = client.post("/api/v1/senders", json={
        "email": email,
        "script_url": "https://script.google.com/macros/s/AKfycbytest/exec",
        "auth_token": "secret_token_12345"
    }, headers=headers)
    assert relay_res.status_code == 201
    relay_id = relay_res.json()["id"]

    # Mark relay ACTIVE
    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok", "remaining_quota": 480}'
        mock_url.return_value.__enter__.return_value = mock_resp
        test_res = client.post(f"/api/v1/senders/{relay_id}/test", headers=headers)
        assert test_res.status_code == 200

    # Quick send to 1 recipient
    with patch("apps.worker.apps_script_relay.AppsScriptRelayClient.send_email") as mock_send:
        mock_send.return_value = {"status": "SENT", "remaining_quota": 479, "message_id": "<test-msg-id@google.com>"}
        
        send_res = client.post("/api/v1/ai/quick-send", json={
            "recipients": ["Recruiter <recruiter@stripe.com>"],
            "subject": "Application for Senior Engineer",
            "body_text": "Hi {name}, attaching my resume for the open role at {company}.",
            "send_now": True,
            "attach_resume": False
        }, headers=headers)

        assert send_res.status_code == 200
        data = send_res.json()
        assert data["status"] == "SENT"
        assert data["sent_count"] == 1
        assert data["remaining_quota"] == 479
        mock_send.assert_called_once()


def test_quick_send_auto_schedules_if_large_batch():
    token, _ = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Send with 6 leads (> 5 leads -> auto-schedules to respect 30/day cap)
    leads = [f"lead{i}@example.com" for i in range(6)]
    send_res = client.post("/api/v1/ai/quick-send", json={
        "recipients": leads,
        "subject": "Outreach",
        "body_text": "Hello",
        "send_now": True,
        "attach_resume": False
    }, headers=headers)

    assert send_res.status_code == 200
    data = send_res.json()
    assert data["status"] == "SCHEDULED"
    assert "safe 30/day automated dispatch" in data["message"]
