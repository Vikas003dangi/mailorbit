import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_signup_login_lifecycle():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "SuperSecurePassword123!"

    # 1. Signup
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "timezone": "Asia/Kolkata"},
    )
    assert signup_res.status_code == 201
    data = signup_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email.lower()
    assert data["user"]["timezone"] == "Asia/Kolkata"

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 2. Duplicate signup fails with 409
    dup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert dup_res.status_code == 409

    # 3. Login with correct password
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data

    # 4. Login with wrong password
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 5. Access /me with token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email.lower()

    # 6. Access /me without token fails
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # 7. Refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()
