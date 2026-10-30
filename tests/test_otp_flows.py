import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient

from apps.api.dependencies import SessionFactory
from apps.api.main import app
from packages.shared.schema import EmailOTP, User

client = TestClient(app)


def test_signup_otp_flow():
    test_email = f"user_{uuid.uuid4().hex[:6]}@example.com"

    # Step 1: Request signup OTP
    res = client.post("/api/v1/auth/signup-otp", json={"email": test_email, "name": "Vikas Dev"})
    assert res.status_code == 200
    assert "dispatched" in res.json()["message"]

    # Retrieve stored OTP from DB for verification
    with SessionFactory() as db:
        otp_record = db.query(EmailOTP).filter(EmailOTP.email == test_email, EmailOTP.purpose == "signup").first()
        assert otp_record is not None
        raw_otp = "854321"
        otp_record.otp_hash = hashlib.sha256(raw_otp.encode()).hexdigest()
        db.commit()

    # Step 2: Try mismatched passwords -> fails
    res_fail = client.post("/api/v1/auth/verify-signup-otp", json={
        "email": test_email,
        "otp": "854321",
        "password": "Password123!",
        "confirm_password": "MismatchPassword!",
        "name": "Vikas Dev",
    })
    assert res_fail.status_code == 400

    # Step 3: Verify with real OTP hash
    res_ok = client.post("/api/v1/auth/verify-signup-otp", json={
        "email": test_email,
        "otp": raw_otp,
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!",
        "name": "Vikas Dev",
    })
    assert res_ok.status_code == 201
    data = res_ok.json()
    assert "access_token" in data
    assert data["user"]["is_email_verified"] is True
    assert data["user"]["email"] == test_email


def test_forgot_and_reset_password_otp():
    test_email = f"reset_{uuid.uuid4().hex[:6]}@example.com"
    from packages.shared.auth import hash_password

    # Create active user
    with SessionFactory() as db:
        user = User(
            email=test_email,
            password_hash=hash_password("OldPassword123!"),
            is_email_verified=True,
        )
        db.add(user)
        db.commit()

    # Request reset OTP
    res = client.post("/api/v1/auth/forgot-password-otp", json={"email": test_email})
    assert res.status_code == 200

    # Retrieve OTP record and mock valid code
    raw_otp = "778899"
    with SessionFactory() as db:
        otp_record = db.query(EmailOTP).filter(EmailOTP.email == test_email, EmailOTP.purpose == "forgot_password").first()
        assert otp_record is not None
        otp_record.otp_hash = hashlib.sha256(raw_otp.encode()).hexdigest()
        db.commit()

    # Reset password with OTP
    res_reset = client.post("/api/v1/auth/reset-password-otp", json={
        "email": test_email,
        "otp": raw_otp,
        "new_password": "NewSecretPassword456!",
        "confirm_password": "NewSecretPassword456!",
    })
    assert res_reset.status_code == 200

    # Verify login with new password
    res_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "NewSecretPassword456!"})
    assert res_login.status_code == 200


def test_change_and_delete_account_otp():
    test_email = f"delete_{uuid.uuid4().hex[:6]}@example.com"
    from packages.shared.auth import hash_password

    with SessionFactory() as db:
        user = User(
            email=test_email,
            password_hash=hash_password("MasterKey123!"),
            is_email_verified=True,
        )
        db.add(user)
        db.commit()

    # Login to get access token
    res_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "MasterKey123!"})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Request change password OTP
    res_cp_otp = client.post("/api/v1/auth/change-password-otp", headers=headers)
    assert res_cp_otp.status_code == 200

    raw_cp_otp = "445566"
    with SessionFactory() as db:
        otp_rec = db.query(EmailOTP).filter(EmailOTP.email == test_email, EmailOTP.purpose == "change_password").first()
        assert otp_rec is not None
        otp_rec.otp_hash = hashlib.sha256(raw_cp_otp.encode()).hexdigest()
        db.commit()

    # Confirm password change
    res_cp = client.post("/api/v1/auth/confirm-change-password", headers=headers, json={
        "current_password": "MasterKey123!",
        "new_password": "BrandNewKey789!",
        "confirm_password": "BrandNewKey789!",
        "otp": raw_cp_otp,
    })
    assert res_cp.status_code == 200

    # Old token must now be rejected with 401 due to session invalidation on password change
    old_token_res = client.post("/api/v1/auth/delete-account-otp", headers=headers)
    assert old_token_res.status_code == 401

    # Login with new password to get active session
    res_relogin = client.post("/api/v1/auth/login", json={"email": test_email, "password": "BrandNewKey789!"})
    assert res_relogin.status_code == 200
    new_headers = {"Authorization": f"Bearer {res_relogin.json()['access_token']}"}

    # Assert 60-second cooldown is strictly enforced on rapid repeat request
    cooldown_blocked = client.post("/api/v1/auth/delete-account-otp", headers=new_headers)
    assert cooldown_blocked.status_code == 429
    assert "Please wait 60 seconds" in cooldown_blocked.json()["detail"]

    # Clear cooldown record to simulate 60 seconds passing
    from packages.shared.schema import RateLimitRecord
    with SessionFactory() as db:
        db.query(RateLimitRecord).filter(RateLimitRecord.key.like("%otp_cooldown%")).delete()
        db.commit()

    # 2. Request delete account OTP with active session after cooldown
    res_del_otp = client.post("/api/v1/auth/delete-account-otp", headers=new_headers)
    assert res_del_otp.status_code == 200

    raw_del_otp = "990011"
    with SessionFactory() as db:
        del_rec = db.query(EmailOTP).filter(EmailOTP.email == test_email, EmailOTP.purpose == "delete_account").first()
        assert del_rec is not None
        del_rec.otp_hash = hashlib.sha256(raw_del_otp.encode()).hexdigest()
        db.commit()

    # Attempt delete without "DELETE" keyword -> fails
    res_del_fail = client.post("/api/v1/auth/confirm-delete-account", headers=new_headers, json={
        "password": "BrandNewKey789!",
        "confirmation_text": "no",
        "otp": raw_del_otp,
    })
    assert res_del_fail.status_code == 400

    # Confirm delete with "DELETE"
    res_del_ok = client.post("/api/v1/auth/confirm-delete-account", headers=new_headers, json={
        "password": "BrandNewKey789!",
        "confirmation_text": "DELETE",
        "otp": raw_del_otp,
    })
    assert res_del_ok.status_code == 200

    # Confirm user is completely erased
    with SessionFactory() as db:
        deleted_user = db.query(User).filter(User.email == test_email).first()
        assert deleted_user is None



def test_resume_scanner():
    test_email = f"scanner_{uuid.uuid4().hex[:6]}@example.com"
    from packages.shared.auth import hash_password

    with SessionFactory() as db:
        user = User(
            email=test_email,
            password_hash=hash_password("Pass12345!"),
            is_email_verified=True,
            sender_name="Vikas Dangi",
        )
        db.add(user)
        db.commit()

    res_login = client.post("/api/v1/auth/login", json={"email": test_email, "password": "Pass12345!"})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sample_resume = """
    Vikas Dangi — Full Stack Engineer
    Skills: Python, FastAPI, React, Next.js, PostgreSQL, Docker, AI, Gemini LLM.
    Experience: 3 years building scalable distributed microservices and autonomous email agents.
    """

    res_scan = client.post("/api/v1/ai/scan-resume", headers=headers, json={"resume_text": sample_resume})
    assert res_scan.status_code == 200
    data = res_scan.json()
    assert "Python" in data["skills"]
    assert "React" in data["skills"]
    assert "job_application" in data["suggested_templates"]
    assert "referral_request" in data["suggested_templates"]
    assert "founder_direct" in data["suggested_templates"]
    assert "Vikas Dangi" in data["suggested_templates"]["job_application"]["body"]
