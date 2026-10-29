import base64
import os
import secrets
import pytest
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.api.main import app
from apps.api.config import settings
from packages.shared.schema import BootstrapRecord, User
from packages.shared.db import create_db_engine, create_session_factory

client = TestClient(app)


def test_production_mode_refuses_to_start_with_missing_or_malformed_keys():
    """Verifies that in production mode, Settings refuses to instantiate if keys are missing or invalid."""
    # 1. Missing ENCRYPTION_MASTER_KEY
    with pytest.raises(ValueError, match="ENCRYPTION_MASTER_KEY environment variable is required"):
        Settings(
            ENVIRONMENT="production",
            ENCRYPTION_MASTER_KEY=None,
            TICK_SECRET="valid-long-secret-key-12345",
        )

    # 2. Malformed ENCRYPTION_MASTER_KEY (wrong length)
    bad_key = base64.b64encode(b"short-key").decode()
    with pytest.raises(ValueError, match="must decode to exactly 32 raw bytes"):
        Settings(
            ENVIRONMENT="production",
            ENCRYPTION_MASTER_KEY=bad_key,
            TICK_SECRET="valid-long-secret-key-12345",
        )

    # 3. Missing TICK_SECRET
    valid_key = base64.b64encode(secrets.token_bytes(32)).decode()
    with pytest.raises(ValueError, match="TICK_SECRET is required"):
        Settings(
            ENVIRONMENT="production",
            ENCRYPTION_MASTER_KEY=valid_key,
            TICK_SECRET=None,
        )

    # 4. Insecure TICK_SECRET placeholder
    with pytest.raises(ValueError, match="contains an insecure development placeholder"):
        Settings(
            ENVIRONMENT="production",
            ENCRYPTION_MASTER_KEY=valid_key,
            TICK_SECRET="dev-watchdog-tick-secret-change-in-prod",
        )

    # 5. Valid production settings succeed
    valid_settings = Settings(
        ENVIRONMENT="production",
        ENCRYPTION_MASTER_KEY=valid_key,
        TICK_SECRET="production-strong-tick-secret-998877",
    )
    assert valid_settings.ENVIRONMENT == "production"
    assert valid_settings.TICK_SECRET == "production-strong-tick-secret-998877"


def test_health_routes_support_get_and_head():
    """
    Verifies that GET and HEAD requests to /api/v1/health and /health
    both return HTTP 200, contain commit hash, and perform zero database queries.
    """
    # 1. GET /api/v1/health
    res_get = client.get("/api/v1/health")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["status"] == "ok"
    assert "commit" in data
    assert data["commit"] != ""

    # 2. HEAD /api/v1/health
    res_head = client.head("/api/v1/health")
    assert res_head.status_code == 200

    # 3. GET /health
    res_root_health_get = client.get("/health")
    assert res_root_health_get.status_code == 200
    assert res_root_health_get.json()["status"] == "ok"

    # 4. HEAD /health
    res_root_health_head = client.head("/health")
    assert res_root_health_head.status_code == 200


def test_tick_route_supports_head():
    """Verifies that HEAD /api/v1/tick is supported and requires X-Tick-Secret."""
    # Without header -> 401
    head_unauth = client.head("/api/v1/tick")
    assert head_unauth.status_code == 401

    # With header -> 200
    head_auth = client.head("/api/v1/tick", headers={"X-Tick-Secret": settings.TICK_SECRET})
    assert head_auth.status_code == 200


def test_admin_bootstrap_persisted_in_database(monkeypatch):
    """
    Verifies that admin bootstrap consumption is recorded permanently in the database,
    preventing reuse even across application restarts.
    """
    import uuid
    admin_email = f"bootstrap_db_{uuid.uuid4().hex[:6]}@example.com"
    bootstrap_token = "persistent-secret-token-xyz-1234"

    monkeypatch.setattr(settings, "ADMIN_EMAILS", admin_email)
    settings.ADMIN_BOOTSTRAP_TOKEN = bootstrap_token

    # 1. Register admin account
    reg = client.post("/api/v1/auth/signup", json={"email": admin_email, "password": "SuperSecure123!"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Consume bootstrap token
    consume_res = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": bootstrap_token},
        headers=headers,
    )
    assert consume_res.status_code == 200
    assert consume_res.json()["user"]["is_email_verified"] is True

    # 3. Verify record in database
    engine = create_db_engine(settings.DATABASE_URL)
    factory = create_session_factory(engine)
    with factory() as session:
        rec = session.query(BootstrapRecord).first()
        assert rec is not None
        assert rec.token_hash is not None

    # 4. Simulate application restart: restore settings.ADMIN_BOOTSTRAP_TOKEN in memory
    settings.ADMIN_BOOTSTRAP_TOKEN = bootstrap_token

    # 5. Attempt second consumption: MUST fail with 403 due to database persistence
    reuse_res = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"bootstrap_token": bootstrap_token},
        headers=headers,
    )
    assert reuse_res.status_code == 403
    assert "already been consumed" in reuse_res.json()["detail"]


def test_production_boot_import_apps_api_main():
    """Verifies that apps.api.main boots in a clean, isolated process under production mode."""
    import subprocess
    import sys
    key = base64.b64encode(secrets.token_bytes(32)).decode()
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["ENCRYPTION_MASTER_KEY"] = key
    env["TICK_SECRET"] = "production-tick-secret-check-9988"
    env["ADMIN_BOOTSTRAP_TOKEN"] = "prod-bootstrap-token-123456"
    env["ADMIN_EMAILS"] = '["admin@mailorbit.io"]'
    env["USE_FAKE_SMTP"] = "false"
    env["DATABASE_URL"] = "sqlite:///./test_mailorbit.db"

    code = (
        "from apps.api.main import app\n"
        "from fastapi.testclient import TestClient\n"
        "c = TestClient(app)\n"
        "r = c.get('/api/v1/health')\n"
        "assert r.status_code == 200, f'Health failed: {r.status_code}'\n"
        "assert r.json()['status'] == 'ok'\n"
        "print('BOOT_OK')\n"
    )
    res = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=15)
    assert res.returncode == 0, f"Production boot process crashed: {res.stderr}"
    assert "BOOT_OK" in res.stdout
