import uuid
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_profile_read_and_update():
    email = f"profile_test_{uuid.uuid4().hex[:6]}@example.com"
    password = "StrongPassword999!"

    # Signup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert signup_res.status_code == 201
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get empty initial profile
    get_res = client.get("/api/v1/profile", headers=headers)
    assert get_res.status_code == 200
    profile = get_res.json()
    assert profile["skills"] == []
    assert profile["links"] == {}

    # Update profile
    update_data = {
        "full_name": "Vikas Dangi",
        "phone": "+91 9876543210",
        "links": {"github": "https://github.com/Vikas003dangi", "portfolio": "https://vikas.dev"},
        "skills": ["Python", "FastAPI", "PostgreSQL", "Next.js"],
        "experience": [{"role": "Senior Developer", "company": "Tech Corp", "years": 3}],
        "summary": "Full-stack developer with focus on automated outreach systems.",
    }
    put_res = client.put("/api/v1/profile", json=update_data, headers=headers)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["full_name"] == "Vikas Dangi"
    assert "FastAPI" in updated["skills"]
    assert updated["links"]["github"] == "https://github.com/Vikas003dangi"

    # Verify persistence
    get_again = client.get("/api/v1/profile", headers=headers)
    assert get_again.status_code == 200
    assert get_again.json()["full_name"] == "Vikas Dangi"

