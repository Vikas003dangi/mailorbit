import pytest
import uuid
from fastapi.testclient import TestClient

from apps.api.config import settings
from apps.api.main import app
from apps.api.services.keyword_matcher import extract_keywords, match_profile_to_jd
from packages.shared.auth import create_access_token, hash_password
from packages.shared.db import create_db_engine, create_session_factory
from packages.shared.schema import Profile, User


def test_keyword_extraction():
    sample_text = """
    We are looking for a Senior Fullstack Engineer with expertise in Python, FastAPI, and Next.js.
    Experience with PostgreSQL, Docker, and CI/CD pipelines is required.
    Familiarity with Machine Learning and Redis is a huge plus!
    """
    keywords = extract_keywords(sample_text)
    assert "python" in keywords
    assert "fastapi" in keywords
    assert "next.js" in keywords
    assert "postgresql" in keywords
    assert "docker" in keywords
    assert "ci/cd" in keywords
    assert "machine learning" in keywords
    assert "redis" in keywords


def test_match_profile_to_jd_metrics():
    profile_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"]
    jd = """
    Requirements:
    - Strong proficiency in Python and FastAPI.
    - Solid knowledge of PostgreSQL and Docker.
    - Hands-on experience with Kubernetes and Kafka.
    """
    res = match_profile_to_jd(profile_skills=profile_skills, jd_text=jd)

    assert "python" in res["matched_skills"]
    assert "fastapi" in res["matched_skills"]
    assert "postgresql" in res["matched_skills"]
    assert "docker" in res["matched_skills"]

    assert "kubernetes" in res["missing_skills"]
    assert "kafka" in res["missing_skills"]

    # 4 matched out of 6 total JD skills = 67%
    assert 60 <= res["match_score"] <= 70
    assert "Strong technical match" in res["pitch_angle"] or "Moderate match" in res["pitch_angle"]


def test_match_profile_to_jd_edge_cases():
    # Empty JD
    res_empty_jd = match_profile_to_jd(profile_skills=["Python", "FastAPI"], jd_text="")
    assert res_empty_jd["match_score"] == 100
    assert "python" in res_empty_jd["matched_skills"]

    # Zero match
    res_zero = match_profile_to_jd(profile_skills=["Ruby", "Rails"], jd_text="Looking for Swift and Kotlin iOS developer")
    assert res_zero["match_score"] == 0
    assert len(res_zero["matched_skills"]) == 0
    assert "swift" in res_zero["missing_skills"]
    assert "kotlin" in res_zero["missing_skills"]


def test_match_jd_api_endpoint():
    client = TestClient(app)
    unique = uuid.uuid4().hex[:6]
    email = f"jd_test_{unique}@example.com"
    password = "StrongPassword999!"

    # Signup to get real auth token
    signup_res = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert signup_res.status_code == 201
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Populate profile skills
    update_data = {
        "full_name": "JD Tester",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "summary": "Backend software engineer specializing in scalable APIs.",
    }
    put_res = client.put("/api/v1/profile", json=update_data, headers=headers)
    assert put_res.status_code == 200

    payload = {
        "jd_text": "We need a Python developer who knows FastAPI, PostgreSQL, and Kubernetes.",
        "resume_text": "",
    }
    resp = client.post("/api/v1/profile/match-jd", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["match_score"] >= 75
    assert "python" in data["matched_skills"]
    assert "fastapi" in data["matched_skills"]
    assert "postgresql" in data["matched_skills"]
    assert "kubernetes" in data["missing_skills"]
    assert "pitch_angle" in data
