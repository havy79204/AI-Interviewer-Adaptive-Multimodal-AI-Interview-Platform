import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from services.user_store import UserStore

TEST_ADMIN_EMAIL = "pipeline-test-admin@example.test"
TEST_ADMIN_PASSWORD = "test-only-pipeline-password"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        UserStore.create(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, role="admin")
        yield test_client


def test_auth_and_candidate_flow(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    create_candidate = client.post(
        "/api/v1/candidates",
        json={"name": "Jane Doe", "email": "jane@example.com", "phone": "123456", "resume_url": "https://example.com/resume.pdf"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_candidate.status_code == 200
    candidate_id = create_candidate.json()["id"]

    candidate = client.get(f"/api/v1/candidates/{candidate_id}", headers={"Authorization": f"Bearer {token}"})
    assert candidate.status_code == 200
    assert candidate.json()["email"] == "jane@example.com"


def test_interview_report_export_flow(client: TestClient):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-abc", "position": "AI Engineer", "mode": "text"},
        headers={"Authorization": f"Bearer {token}"},
    )
    interview_id = start.json()["interview_id"]

    client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": "turn-report-1", "answer": "I have built Python and PyTorch models and deployed them to production."},
        headers={"Authorization": f"Bearer {token}"},
    )

    report = client.post(
        f"/api/v1/interview/{interview_id}/report",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert report.status_code == 200
    payload = report.json()
    assert payload["interview_id"] == interview_id
    assert payload["report_file"].endswith(".json")
    assert payload["report"]["evaluation_status"] == "complete"
    assert "recruiter's independent hiring decision" in payload["report"]["decision_disclaimer"]
