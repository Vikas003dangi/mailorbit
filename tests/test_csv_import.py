import io
import uuid
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_csv_file_import_with_flexible_headers():
    email = f"csv_user_{uuid.uuid4().hex[:6]}@example.com"
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Password12345!"},
    )
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "Contact Email,Full Name,Company Name,Position\n"
        "anita@companyalpha.com,Anita Sharma,Company Alpha,HR Lead\n"
        "rohit@betasoftware.io,Rohit Verma,Beta Software,Talent Partner\n"
        "duplicate@betasoftware.io,Same Person,Beta Software,Recruiter\n"
        "duplicate@betasoftware.io,Same Person,Beta Software,Recruiter\n"
        "invalid-email-address,Bad User,No Company,None\n"
    )
    files = {
        "file": ("contacts.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }

    res = client.post(
        "/api/v1/contacts/import-csv",
        files=files,
        data={"auto_batch": "false"},
        headers=headers,
    )
    assert res.status_code == 201
    summary = res.json()["summary"]

    assert summary["total_rows"] == 5
    assert summary["imported_count"] == 3  # anita, rohit, duplicate
    assert summary["duplicates_dropped"] == 1
    assert summary["invalid_format_count"] == 1

    # Verify mapped fields
    contacts_res = client.get("/api/v1/contacts", headers=headers)
    assert contacts_res.status_code == 200
    leads = contacts_res.json()
    assert len(leads) == 3
    anita = next(c for c in leads if c["email"] == "anita@companyalpha.com")
    assert anita["name"] == "Anita Sharma"
    assert anita["company"] == "Company Alpha"
    assert anita["role"] == "HR Lead"
