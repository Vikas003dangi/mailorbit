import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.config import settings

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "mailorbit-api"
    assert data["version"] == "0.1.0"


def test_tick_endpoint_requires_secret():
    response = client.post("/api/v1/tick")
    assert response.status_code == 401


def test_tick_endpoint_succeeds_with_secret():
    headers = {"X-Tick-Secret": settings.TICK_SECRET}
    response = client.post("/api/v1/tick", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "jobs_processed" in data


def test_egress_diagnostics_requires_secret():
    response = client.get("/api/v1/diagnostics/egress")
    assert response.status_code == 401


def test_egress_diagnostics_succeeds_with_secret():
    headers = {"X-Tick-Secret": settings.TICK_SECRET}
    response = client.get("/api/v1/diagnostics/egress", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "smtp_587" in data
    assert "script_tcp_443" in data
    assert "script_https_get" in data
    assert data["smtp_587"]["status"] in ["PASS", "FAIL"]
    assert data["script_tcp_443"]["status"] in ["PASS", "FAIL"]
    assert data["script_https_get"]["status"] in ["PASS", "FAIL"]
