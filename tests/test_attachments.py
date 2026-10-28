import io
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from apps.api.main import app

client = TestClient(app)


def get_authenticated_headers():
    email = f"doc_tester_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@patch("apps.api.routers.attachments.upload_attachment")
@patch("apps.api.routers.attachments.delete_attachment")
def test_attachments_full_lifecycle(mock_delete, mock_upload):
    """
    TRD Milestone M3 Acceptance Test:
    - Upload document (PDF resume)
    - Validate MIME types and size constraints
    - List user's document library
    - Link document to campaign purpose
    - Verify cascade and unlinking
    """
    headers = get_authenticated_headers()

    # Mock Cloudinary responses so unit tests never hit live third-party network
    mock_upload.return_value = {
        "file_url": "https://res.cloudinary.com/test_cloud/image/upload/v12345/resume.pdf",
        "cloudinary_public_id": "mailorbit/attachments/test_resume_public_id",
        "size_bytes": 1024,
        "filename": "Senior_SWE_Resume.pdf",
        "content_type": "application/pdf",
    }
    mock_delete.return_value = True

    # 1. Create a campaign purpose to link attachments to
    purpose_res = client.post(
        "/api/v1/purposes",
        json={"name": "Senior SWE Inbound Applications"},
        headers=headers,
    )
    assert purpose_res.status_code == 201
    purpose_id = purpose_res.json()["id"]

    # 2. Upload a valid PDF file
    fake_pdf_content = b"%PDF-1.4 simulated pdf document binary content for testing"
    files = {
        "file": ("Senior_SWE_Resume.pdf", io.BytesIO(fake_pdf_content), "application/pdf")
    }
    upload_res = client.post("/api/v1/attachments/upload", files=files, headers=headers)
    assert upload_res.status_code == 201
    att = upload_res.json()
    assert att["filename"] == "Senior_SWE_Resume.pdf"
    assert att["file_url"] == "https://res.cloudinary.com/test_cloud/image/upload/v12345/resume.pdf"
    assert att["cloudinary_public_id"] == "mailorbit/attachments/test_resume_public_id"
    attachment_id = att["id"]

    # 3. List user's attachments
    list_res = client.get("/api/v1/attachments", headers=headers)
    assert list_res.status_code == 200
    attachments_list = list_res.json()
    assert len(attachments_list) >= 1
    assert any(a["id"] == attachment_id for a in attachments_list)

    # 4. Get single attachment details
    get_res = client.get(f"/api/v1/attachments/{attachment_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == attachment_id

    # 5. Link attachment to campaign purpose
    link_res = client.post(
        f"/api/v1/purposes/{purpose_id}/attachments/{attachment_id}",
        headers=headers,
    )
    assert link_res.status_code == 200

    # 6. Verify purpose shows linked attachment
    purpose_atts_res = client.get(f"/api/v1/purposes/{purpose_id}/attachments", headers=headers)
    assert purpose_atts_res.status_code == 200
    purpose_atts = purpose_atts_res.json()
    assert len(purpose_atts) == 1
    assert purpose_atts[0]["id"] == attachment_id

    # 7. Unlink attachment from purpose
    unlink_res = client.delete(
        f"/api/v1/purposes/{purpose_id}/attachments/{attachment_id}",
        headers=headers,
    )
    assert unlink_res.status_code == 204

    # Verify purpose now has 0 attachments
    purpose_atts_after = client.get(f"/api/v1/purposes/{purpose_id}/attachments", headers=headers)
    assert len(purpose_atts_after.json()) == 0

    # 8. Delete attachment from library
    del_res = client.delete(f"/api/v1/attachments/{attachment_id}", headers=headers)
    assert del_res.status_code == 204
    mock_delete.assert_called_once()

    # Verify attachment is gone
    get_after_del = client.get(f"/api/v1/attachments/{attachment_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_attachment_validation_rules():
    """Verify that file size > 5 MB and invalid content-types are rejected."""
    headers = get_authenticated_headers()

    # A. Reject file exceeding 5 MB limit
    oversized_content = b"0" * (5 * 1024 * 1024 + 10)  # 5MB + 10 bytes
    files = {
        "file": ("huge_file.pdf", io.BytesIO(oversized_content), "application/pdf")
    }
    oversize_res = client.post("/api/v1/attachments/upload", files=files, headers=headers)
    assert oversize_res.status_code == 400
    assert "exceeds maximum allowed limit" in oversize_res.json()["detail"]

    # B. Reject dangerous/unsupported file types (e.g., .exe)
    invalid_files = {
        "file": ("malware.exe", io.BytesIO(b"executable content"), "application/x-msdownload")
    }
    invalid_res = client.post("/api/v1/attachments/upload", files=invalid_files, headers=headers)
    assert invalid_res.status_code == 400
    assert "Unsupported file type" in invalid_res.json()["detail"]
