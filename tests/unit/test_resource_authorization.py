from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from apps.api.main import app
from services.auth_service import decode_token, issue_token
from services.database import AccessAuditRecord, SessionLocal
from services.user_store import UserStore


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user(role: str) -> tuple[dict, dict[str, str]]:
    email = f"{role}-{uuid4()}@example.com"
    user = UserStore.create(email, "secret123", role=role)
    token = issue_token(email, role)
    return user, {"Authorization": f"Bearer {token}"}


def test_unspecified_user_role_defaults_to_candidate(client: TestClient):
    email = f"default-role-{uuid4()}@example.com"
    user = UserStore.create(email, "secret123")

    assert user["role"] == "candidate"
    assert decode_token(issue_token(email))["role"] == "candidate"


def create_candidate(client: TestClient, headers: dict[str, str], email: str | None = None) -> dict:
    email = email or f"candidate-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/candidates",
        json={"name": "Synthetic Candidate", "email": email},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def start_interview(client: TestClient, headers: dict[str, str], candidate_id: str) -> str:
    response = client.post(
        "/api/v1/interview/start",
        json={
    "candidate_id": candidate_id,
    "position": "Synthetic Engineer",
    "job_description": (
        "We are seeking a Synthetic Engineer with Python, "
        "REST APIs, SQL, and problem-solving skills."
    ),
},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["interview_id"]


def test_candidate_profile_and_interview_are_self_scoped(client: TestClient):
    user_a, headers_a = create_user("candidate")
    user_b, headers_b = create_user("candidate")
    candidate_a = create_candidate(client, headers_a, user_a["email"])
    candidate_b = create_candidate(client, headers_b, user_b["email"])
    interview_a = start_interview(client, headers_a, candidate_a["id"])
    interview_b = start_interview(client, headers_b, candidate_b["id"])

    assert client.get(f"/api/v1/candidates/{candidate_a['id']}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/candidates/{candidate_b['id']}", headers=headers_a).status_code == 404
    assert client.get(f"/api/v1/interview/{interview_a}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/interview/{interview_a}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/interview/{interview_b}", headers=headers_a).status_code == 404
    assert [item["id"] for item in client.get("/api/v1/candidates", headers=headers_a).json()] == [
        candidate_a["id"]
    ]
    assert [item["interview_id"] for item in client.get("/api/v1/interviews", headers=headers_a).json()] == [
        interview_a
    ]
    assert client.post(
        f"/api/v1/interview/{interview_a}/report", headers=headers_a
    ).status_code == 200
    assert client.post(
        f"/api/v1/interview/{interview_a}/report", headers=headers_b
    ).status_code == 404
    assert client.post(
        f"/api/v1/interview/{interview_b}/report", headers=headers_a
    ).status_code == 404
    assert client.patch(
        f"/api/v1/candidates/{candidate_b['id']}",
        json={"name": "Tampered Name"},
        headers=headers_a,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/candidates/{candidate_a['id']}",
        json={"owner_user_id": "forged-owner"},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/v1/interview/start",
        json={
            "candidate_id": candidate_a["id"],
            "position": "Synthetic Engineer",
            "owner_user_id": "forged-owner",
        },
        headers=headers_a,
    ).status_code == 422


def test_recruiter_candidate_interview_and_report_access_is_owner_scoped(client: TestClient):
    _, headers_a = create_user("recruiter")
    _, headers_b = create_user("recruiter")
    candidate_a = create_candidate(client, headers_a)
    candidate_b = create_candidate(client, headers_b)
    interview_a = start_interview(client, headers_a, candidate_a["id"])

    assert client.get(f"/api/v1/candidates/{candidate_a['id']}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/candidates/{candidate_a['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/interview/{interview_a}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/interview/{interview_a}", headers=headers_b).status_code == 404
    assert {
        item["id"] for item in client.get("/api/v1/candidates", headers=headers_b).json()
    } == {candidate_b["id"]}
    assert client.get("/api/v1/interviews", headers=headers_b).json() == []
    assert client.post(
        f"/api/v1/interview/{interview_a}/report", headers=headers_a
    ).status_code == 200
    assert client.post(
        f"/api/v1/interview/{interview_a}/report", headers=headers_b
    ).status_code == 404
    assert client.post(
        "/api/v1/interview/start",
        json={"candidate_id": candidate_a["id"], "position": "Synthetic Engineer"},
        headers=headers_b,
    ).status_code == 404
    assert candidate_b["id"] != candidate_a["id"]


def test_anonymous_candidate_and_report_access_is_denied(client: TestClient):
    _, headers = create_user("recruiter")
    candidate = create_candidate(client, headers)
    interview_id = start_interview(client, headers, candidate["id"])

    assert client.get("/api/v1/candidates").status_code == 401
    assert client.get(f"/api/v1/interview/{interview_id}").status_code == 401
    assert client.post(f"/api/v1/interview/{interview_id}/report").status_code == 401


def test_admin_resource_access_is_persistently_audited(client: TestClient):
    admin, admin_headers = create_user("admin")
    candidate = create_candidate(client, admin_headers)
    interview_id = start_interview(client, admin_headers, candidate["id"])
    assert client.get(f"/api/v1/interview/{interview_id}", headers=admin_headers).status_code == 200
    assert client.post(
        f"/api/v1/interview/{interview_id}/report", headers=admin_headers
    ).status_code == 200

    with SessionLocal() as session:
        events = session.execute(
            select(AccessAuditRecord).where(AccessAuditRecord.actor_user_id == admin["id"])
        ).scalars().all()
    assert {(event.action, event.resource_type, event.resource_id) for event in events} >= {
        ("create", "candidate", candidate["id"]),
        ("create", "interview", interview_id),
        ("read", "interview", interview_id),
    }


def test_generic_websocket_requires_authentication_and_resource_access(client: TestClient):
    owner, owner_headers = create_user("recruiter")
    candidate = create_candidate(client, owner_headers)
    interview_id = start_interview(client, owner_headers, candidate["id"])
    _, other_headers = create_user("recruiter")
    other_token = other_headers["Authorization"].removeprefix("Bearer ")
    owner_token = issue_token(owner["email"], owner["role"])

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/interview/{interview_id}"):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/interview/{interview_id}?token={other_token}"):
            pass
    with client.websocket_connect(f"/ws/interview/{interview_id}?token={owner_token}") as websocket:
        assert websocket.receive_json()["type"] == "connected"

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/ws/interview/{interview_id}/voice?token={other_token}"
        ):
            pass
