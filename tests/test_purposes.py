import uuid
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_purpose_crud_lifecycle():
    email = f"purpose_user_{uuid.uuid4().hex[:6]}@example.com"
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password12345!"},
    )
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Purpose
    create_payload = {
        "name": "Full-Stack Python Job Applications",
        "description": "Cold outreach to tech recruiters for Python & AI roles",
        "default_subject_template": "Application: {{role}} | {{name}}",
        "default_body_template": "Hi {{first_name}}, I noticed the open {{role}} role at {{company}}...",
    }
    res = client.post("/api/v1/purposes", json=create_payload, headers=headers)
    assert res.status_code == 201
    purpose = res.json()
    purpose_id = purpose["id"]
    assert purpose["name"] == create_payload["name"]
    assert purpose["is_active"] is True

    # 2. List Purposes
    list_res = client.get("/api/v1/purposes", headers=headers)
    assert list_res.status_code == 200
    purposes = list_res.json()
    assert len(purposes) == 1
    assert purposes[0]["id"] == purpose_id

    # 3. Update Purpose
    update_res = client.put(
        f"/api/v1/purposes/{purpose_id}",
        json={"name": "Senior AI & Full-Stack Outreach"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Senior AI & Full-Stack Outreach"

    # 4. Delete Purpose
    del_res = client.delete(f"/api/v1/purposes/{purpose_id}", headers=headers)
    assert del_res.status_code == 204

    # 5. Verify deleted
    get_res = client.get(f"/api/v1/purposes/{purpose_id}", headers=headers)
    assert get_res.status_code == 404

