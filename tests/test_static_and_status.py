from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_status_page_returns_html():
    response = client.get("/status")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "MailOrbit System Architecture & Status" in response.text
    assert "Render Web Service" in response.text


def test_root_serves_static_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "MailOrbit" in response.text
