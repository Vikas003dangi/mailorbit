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

    # 8. Server-side logout clears cookie
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"


def test_forgot_password_and_reset_flow():
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "OriginalPassword123!"

    # 1. Sign up user
    client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})

    # 2. Forgot password request (non-existent email gives identical message)
    non_existent = client.post("/api/v1/auth/forgot-password", json={"email": "nobody_exists_here_xyz@example.com"})
    assert non_existent.status_code == 200
    msg_non_existent = non_existent.json()["message"]

    real_req = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert real_req.status_code == 200
    assert real_req.json()["message"] == msg_non_existent

    # 3. Retrieve hashed token from DB for unit verification
    from packages.shared.db import create_db_engine, create_session_factory
    from packages.shared.schema import User
    from apps.api.config import settings
    engine = create_db_engine(settings.DATABASE_URL)
    factory = create_session_factory(engine)
    with factory() as session:
        user = session.query(User).filter(User.email == email).first()
        assert user.reset_token_hash is not None
        # Set a known raw token hash for testing reset
        import hashlib
        known_raw = "test_reset_token_12345"
        user.reset_token_hash = hashlib.sha256(known_raw.encode()).hexdigest()
        session.commit()

    # 4. Bad token fails
    bad_reset = client.post("/api/v1/auth/reset-password", json={"token": "invalid_token", "new_password": "NewPassword123!"})
    assert bad_reset.status_code == 400

    # 5. Good token succeeds
    good_reset = client.post("/api/v1/auth/reset-password", json={"token": known_raw, "new_password": "NewPassword123!"})
    assert good_reset.status_code == 200
    assert good_reset.json()["status"] == "success"

    # 6. Verify login with new password
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": "NewPassword123!"})
    assert new_login.status_code == 200
