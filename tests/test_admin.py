import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.config import settings
from packages.shared.auth import create_access_token

client = TestClient(app)


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


def test_admin_allowed_for_superuser(monkeypatch):
    test_super_email = f"superuser_{uuid.uuid4().hex[:6]}@example.com"
    import apps.api.dependencies
    monkeypatch.setattr(apps.api.dependencies, "SUPERUSER_EMAILS", {test_super_email})

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
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
    monkeypatch.setattr(apps.api.dependencies, "SUPERUSER_EMAILS", {test_super_email})

    reg = client.post("/api/v1/auth/signup", json={"email": test_super_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/admin/system", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "host" in data
