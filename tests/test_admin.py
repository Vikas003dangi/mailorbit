import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.config import settings
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import User

client = TestClient(app)


def mark_user_verified(email: str):
    engine = create_db_engine(settings.DATABASE_URL)
    factory = create_session_factory(engine)
    with factory() as session:
        user = session.query(User).filter(User.email == email).first()
        if user:
            user.is_email_verified = True
            session.commit()


def test_admin_forbidden_for_regular_user():
    # Register regular user
    email = f"regular_{uuid.uuid4().hex[:6]}@example.com"
    reg = client.post("/api/v1/auth/signup", json={"email": email, "password": "SecurePassword123!"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 403
    assert "Superuser privilege required" in res.json()["detail"]


def test_freshly_registered_admin_email_without_verification_is_forbidden(monkeypatch):
    """
    Asserts that a freshly registered account whose email is in ADMIN_EMAILS
    CANNOT access admin endpoints while is_email_verified is False.
    """
    test_super_email = f"unverified_admin_{uuid.uuid4().hex[:6]}@example.com"
    monkeypatch.setattr(settings, "ADMIN_EMAILS", test_super_email)

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    assert reg.json()["user"]["is_email_verified"] is False
    assert reg.json()["user"]["is_superuser"] is False
    token = reg.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 403
    assert "Verified email address required" in res.json()["detail"]


def test_admin_bootstrap_token_lifecycle(monkeypatch):
    """
    Tests one-time admin bootstrap token:
    1. Unverified admin uses valid bootstrap token -> elevated & verified
    2. Bootstrap token is immediately consumed and expires (subsequent use fails)
    3. Non-admin email cannot use the bootstrap token
    """
    admin_email = f"bootstrap_admin_{uuid.uuid4().hex[:6]}@example.com"
    non_admin_email = f"bootstrap_nonadmin_{uuid.uuid4().hex[:6]}@example.com"

    monkeypatch.setattr(settings, "ADMIN_EMAILS", admin_email)
    settings.ADMIN_BOOTSTRAP_TOKEN = "one-time-secret-bootstrap-token-xyz"

    # Register admin email
    reg = client.post("/api/v1/auth/signup", json={"email": admin_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    admin_token = reg.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register non-admin email
    reg_non = client.post("/api/v1/auth/signup", json={"email": non_admin_email, "password": "SuperSecure123!"})
    assert reg_non.status_code == 201
    non_token = reg_non.json()["access_token"]
    non_headers = {"Authorization": f"Bearer {non_token}"}

    # 1. Non-admin attempts to use bootstrap token -> 403 Forbidden
    res_non = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": "one-time-secret-bootstrap-token-xyz"},
        headers=non_headers,
    )
    assert res_non.status_code == 403
    assert "not authorized" in res_non.json()["detail"]

    # 2. Admin uses wrong bootstrap token -> 403 Forbidden
    res_wrong = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": "wrong-token-abc"},
        headers=admin_headers,
    )
    assert res_wrong.status_code == 403
    assert "Invalid or expired" in res_wrong.json()["detail"]

    # 3. Admin uses valid bootstrap token -> 200 Success
    res_valid = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": "one-time-secret-bootstrap-token-xyz"},
        headers=admin_headers,
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["user"]["is_email_verified"] is True
    assert res_valid.json()["user"]["is_superuser"] is True
    assert settings.ADMIN_BOOTSTRAP_TOKEN is None  # consumed in-memory

    # 4. Attempting to reuse the bootstrap token -> 403 Forbidden
    res_reuse = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": "one-time-secret-bootstrap-token-xyz"},
        headers=admin_headers,
    )
    assert res_reuse.status_code == 403
    assert (
        "Invalid or expired" in res_reuse.json()["detail"]
        or "already been consumed" in res_reuse.json()["detail"]
    )

    # 5. Admin now has full admin access
    stats_res = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200


def test_admin_allowed_for_superuser(monkeypatch):
    test_super_email = f"superuser_{uuid.uuid4().hex[:6]}@example.com"
    import apps.api.dependencies
    monkeypatch.setattr(apps.api.dependencies, "get_admin_emails", lambda: {test_super_email})

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    mark_user_verified(test_super_email)
    token = reg.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_superuser"] is True
    assert "totals" in data
    assert "users" in data["totals"]
    assert "batches" in data["totals"]


def test_admin_system_health_endpoint(monkeypatch):
    test_super_email = f"superuser_health_{uuid.uuid4().hex[:6]}@example.com"
    import apps.api.dependencies
    monkeypatch.setattr(apps.api.dependencies, "get_admin_emails", lambda: {test_super_email})

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    mark_user_verified(test_super_email)
    token = reg.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/admin/system", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "host" in data


def test_admin_capabilities(monkeypatch):
    test_super_email = f"superuser_caps_{uuid.uuid4().hex[:6]}@example.com"
    import apps.api.dependencies
    monkeypatch.setattr(apps.api.dependencies, "get_admin_emails", lambda: {test_super_email})

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    mark_user_verified(test_super_email)
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List users
    users_res = client.get("/api/v1/admin/users", headers=headers)
    assert users_res.status_code == 200
    users_data = users_res.json()
    assert isinstance(users_data, list)
    assert len(users_data) >= 1

    # 2. List batches
    batches_res = client.get("/api/v1/admin/batches", headers=headers)
    assert batches_res.status_code == 200
    assert isinstance(batches_res.json(), list)

    # 3. Trigger tick
    tick_res = client.post("/api/v1/admin/trigger-tick", headers=headers)
    assert tick_res.status_code == 200
    assert "status" in tick_res.json()
