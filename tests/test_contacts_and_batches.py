import uuid
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_bulk_350_contacts_import_and_auto_batching():
    """
    TRD Milestone M2 Core Acceptance Test:
    - 350 valid contacts import in one single go
    - Invalid formats flagged and rejected
    - Duplicates detected and dropped
    - Batches of 30 auto-created ('Batch 1', 'Batch 2', ...)
    - Batches renamable via PATCH
    - Inactive contacts listing and reactivation
    """
    email = f"lead_mgr_{uuid.uuid4().hex[:6]}@example.com"
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a campaign purpose
    purpose_res = client.post(
        "/api/v1/purposes",
        json={"name": "Software Engineering Direct Outreach"},
        headers=headers,
    )
    assert purpose_res.status_code == 201
    purpose_id = purpose_res.json()["id"]

    # 2. Build test dataset:
    # - 350 unique valid contacts
    # - 10 duplicate contacts (repeating earlier emails)
    # - 5 invalid email formats
    contacts_payload = []

    # 350 unique leads
    for i in range(1, 351):
        contacts_payload.append({
            "email": f"recruiter_{i}@techcompany{i}.com",
            "name": f"Recruiter {i}",
            "company": f"TechCompany {i}",
            "role": "Technical Hiring Manager",
        })

    # 10 duplicates (duplicates of first 10 leads)
    for i in range(1, 11):
        contacts_payload.append({
            "email": f"recruiter_{i}@techcompany{i}.com",
            "name": f"Duplicate Recruiter {i}",
            "company": f"TechCompany {i}",
            "role": "Technical Hiring Manager",
        })

    # 5 invalid formats
    contacts_payload.extend([
        {"email": "invalid_no_at_sign.com", "name": "Bad Lead 1"},
        {"email": "@nodomain.com", "name": "Bad Lead 2"},
        {"email": "spaces in email@domain.com", "name": "Bad Lead 3"},
        {"email": "", "name": "Empty Lead 4"},
        {"email": "not_an_email", "name": "Bad Lead 5"},
    ])

    assert len(contacts_payload) == 365

    # 3. Import in one go with auto-batching (batch_size=30)
    import_req = {
        "purpose_id": purpose_id,
        "contacts": contacts_payload,
        "auto_batch": True,
        "batch_size": 30,
        "daily_send_time": "10:00",
        "active_days": ["mon", "tue", "wed", "thu", "fri"],
    }
    res = client.post("/api/v1/contacts/import", json=import_req, headers=headers)
    assert res.status_code == 201
    result = res.json()
    summary = result["summary"]

    # Verify import numbers:
    assert summary["total_rows"] == 365
    assert summary["imported_count"] == 350  # Exactly 350 imported!
    assert summary["duplicates_dropped"] == 10  # Exactly 10 duplicates dropped!
    assert summary["invalid_format_count"] == 5  # Exactly 5 invalids rejected!

    # Verify auto-batching:
    # 350 contacts / 30 per batch = 12 batches (11 batches of 30, 1 batch of 20)
    assert result["created_batches_count"] == 12
    assert result["assigned_to_batches_count"] == 350

    # 4. Verify created batches in database
    batches_res = client.get(f"/api/v1/batches?purpose_id={purpose_id}", headers=headers)
    assert batches_res.status_code == 200
    batches = batches_res.json()
    assert len(batches) == 12
    assert batches[0]["name"] == "Batch 1"
    assert batches[0]["size"] == 30
    assert batches[11]["name"] == "Batch 12"
    assert batches[11]["size"] == 20

    # 5. Verify batches are renamable via PATCH
    first_batch_id = batches[0]["id"]
    patch_res = client.patch(
        f"/api/v1/batches/{first_batch_id}",
        json={"name": "Batch 1 - Bangalore AI Startups"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Batch 1 - Bangalore AI Startups"

    # 6. Verify duplicate import prevention against database
    # Attempting to re-import the same contacts must drop all 350 as existing duplicates
    reimport_res = client.post("/api/v1/contacts/import", json=import_req, headers=headers)
    assert reimport_res.status_code == 201
    reimport_summary = reimport_res.json()["summary"]
    assert reimport_summary["imported_count"] == 0
    assert reimport_summary["duplicates_dropped"] == 360  # 10 payload dups + 350 db dups

    # 7. Inactive Contact Handling & Reactivation
    # Pick one contact and simulate failure/bounce
    list_contacts_res = client.get(f"/api/v1/contacts?purpose_id={purpose_id}&limit=5", headers=headers)
    sample_contact = list_contacts_res.json()[0]
    sample_id = sample_contact["id"]

    # Mark contact as BOUNCED
    client.patch(
        f"/api/v1/contacts/{sample_id}",
        json={"status": "BOUNCED", "status_reason": "550 5.1.1 Mailbox does not exist"},
        headers=headers,
    )

    # Verify contact appears in Inactive list with reason
    inactive_res = client.get("/api/v1/contacts/inactive", headers=headers)
    assert inactive_res.status_code == 200
    inactive_leads = inactive_res.json()
    assert len(inactive_leads) == 1
    assert inactive_leads[0]["id"] == sample_id
    assert inactive_leads[0]["status_reason"] == "550 5.1.1 Mailbox does not exist"

    # Reactivate contact
    reactivate_res = client.post(f"/api/v1/contacts/{sample_id}/reactivate", headers=headers)
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["status"] == "PENDING"
    assert reactivate_res.json()["status_reason"] is None

    # Verify inactive list is now empty
    inactive_after = client.get("/api/v1/contacts/inactive", headers=headers)
    assert len(inactive_after.json()) == 0
