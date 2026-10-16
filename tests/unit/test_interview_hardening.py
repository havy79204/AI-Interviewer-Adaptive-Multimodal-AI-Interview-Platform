from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from tracemalloc import start
from uuid import uuid4
from wsgiref import headers

from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.main import app
from services.auth_service import decode_token, issue_token
from services.database import InterviewQuestionRecord, InterviewTurnRecord, SessionLocal
from services.interview_service import InterviewService
from services.user_store import UserStore
from agents.interview_agent.graph import InterviewAgentCore
from tests.unit.test_question_planning import (
    SampleAdaptiveEvaluator,
    _configure_adaptive_service,
)

client = TestClient(app)

def configure_test_planning(monkeypatch):
    service, _ = _configure_adaptive_service(
        monkeypatch,
        SampleAdaptiveEvaluator(),
    )
    return service


def register_and_login(email: str) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def candidate_profile_id(headers: dict[str, str]) -> str:
    token = headers["Authorization"].split(" ", 1)[1]
    email = decode_token(token)["sub"]
    profile = client.post(
        "/api/v1/candidates",
        json={"name": "Test Candidate", "email": email},
        headers=headers,
    )
    assert profile.status_code == 200
    return profile.json()["id"]


def test_registration_cannot_escalate_to_admin():
    client.post(
        "/api/v1/auth/register",
        json={"email": "not-admin@example.com", "password": "password123", "role": "admin"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "not-admin@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "candidate"


def test_recruiter_cannot_submit_answers(monkeypatch):
    configure_test_planning(monkeypatch)
    owner_headers = register_and_login("recruiter-owner@example.com")
    UserStore.create("recruiter@example.com", "password123", role="recruiter")
    recruiter = UserStore.get_by_email("recruiter@example.com")
    recruiter_headers = {"Authorization": f"Bearer {issue_token(recruiter['email'], 'recruiter')}"}
    start = client.post(
        "/api/v1/interview/start",
        json={
        "candidate_id": candidate_profile_id(owner_headers),
        "position": "AI Engineer",
        "job_description": (
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    },
        headers=owner_headers,
    )
    assert start.status_code == 200, (
        f"Interview creation failed: "
        f"status={start.status_code}, response={start.text}"
    )
    interview_id = start.json()["interview_id"]
    
    response = client.post(
        f"/api/v1/interview/{start.json()['interview_id']}/answer",
        json={"turn_id": "recruiter-turn", "answer": "I used Python."},
        headers=recruiter_headers,
    )
    assert response.status_code == 403


def test_user_cannot_access_another_users_interview(monkeypatch):
    configure_test_planning(monkeypatch)
    owner_headers = register_and_login("owner@example.com")
    other_headers = register_and_login("other@example.com")
    start = client.post(
        "/api/v1/interview/start",
        json={
        "candidate_id": candidate_profile_id(owner_headers),
        "position": "AI Engineer",
        "job_description": (
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    },
        headers=owner_headers,
    )
    assert start.status_code == 200, (
    f"Interview creation failed: "
    f"status={start.status_code}, response={start.text}"
)
    interview_id = start.json()["interview_id"]

    response = client.get(f"/api/v1/interview/{interview_id}", headers=other_headers)
    assert response.status_code == 404


def test_concurrent_duplicate_turns_create_one_record(monkeypatch):
    configure_test_planning(monkeypatch)
    headers = register_and_login("concurrent@example.com")
    start = client.post(
        "/api/v1/interview/start",
        json={
        "candidate_id": candidate_profile_id(headers),
        "position": "AI Engineer",
        "job_description": (
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    },
        headers=headers,
    )
    assert start.status_code == 200, (
    f"Interview creation failed: "
    f"status={start.status_code}, response={start.text}"
)
    interview_id = start.json()["interview_id"]
    request = {"turn_id": "concurrent-turn", "answer": "I deployed Python to production."}

    def submit():
        return client.post(
            f"/api/v1/interview/{interview_id}/answer", json=request, headers=headers
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: submit(), range(2)))

    statuses = [response.status_code for response in responses]
    assert sorted(statuses) in ([200, 200], [200, 409])
    if 409 in statuses:
        assert "still processing" in next(
            response.json()["detail"] for response in responses if response.status_code == 409
        )
        replay = submit()
        assert replay.status_code == 200
    with SessionLocal() as session:
        turns = session.execute(
            select(InterviewTurnRecord).where(InterviewTurnRecord.interview_id == interview_id)
        ).scalars().all()
        questions = session.execute(
            select(InterviewQuestionRecord).where(InterviewQuestionRecord.interview_id == interview_id)
        ).scalars().all()
    assert len(turns) == 1
    assert len(questions) == 2
    assert len({question.question_text for question in questions}) == 2


def test_reusing_turn_id_with_different_answer_returns_conflict(monkeypatch):
    configure_test_planning(monkeypatch)
    headers = register_and_login("turn-conflict@example.com")
    start = client.post(
        "/api/v1/interview/start",
        json={
        "candidate_id": candidate_profile_id(headers),
        "position": "AI Engineer",
        "job_description": (
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    },
        headers=headers,
    )
    assert start.status_code == 200, (
    f"Interview creation failed: "
    f"status={start.status_code}, response={start.text}"
)
    interview_id = start.json()["interview_id"]
    first = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": "turn-conflict", "answer": "I used Python."},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": "turn-conflict", "answer": "I used Rust instead."},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    with SessionLocal() as session:
        turns = session.execute(
            select(InterviewTurnRecord).where(
                InterviewTurnRecord.interview_id == interview_id
            )
        ).scalars().all()
    assert len(turns) == 1


def test_stale_processing_turn_can_be_retried(monkeypatch):
    configure_test_planning(monkeypatch)
    headers = register_and_login("recovery@example.com")
    turn_id = f"recovery-turn-{uuid4()}"
    start = client.post(
        "/api/v1/interview/start",
            json={
        "candidate_id": candidate_profile_id(headers),
        "position": "AI Engineer",
        "job_description": (
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    },
        headers=headers,
    )
    assert start.status_code == 200, (
    f"Interview creation failed: "
    f"status={start.status_code}, response={start.text}"
)
    interview_id = start.json()["interview_id"]
    first = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": turn_id, "answer": "I used Python."},
        headers=headers,
    )
    assert first.status_code == 200
    with SessionLocal.begin() as session:
        turn = session.execute(
            select(InterviewTurnRecord).where(InterviewTurnRecord.interview_id == interview_id)
        ).scalar_one()
        turn.status = "processing"
        turn.updated_at = datetime.now(UTC) - timedelta(hours=1)

    retry = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": turn_id, "answer": "I used Python."},
        headers=headers,
    )
    assert retry.status_code == 200


def test_processing_failure_is_marked_retryable(monkeypatch):
    service, _ = _configure_adaptive_service(
        monkeypatch,
        SampleAdaptiveEvaluator(),
    )
    turn_id = f"failed-turn-{uuid4()}"
    state = service.start_interview(
        f"candidate-failure-{uuid4()}",
        "AI Engineer",
        owner_role="admin",
        job_description=(
            "We need an AI Engineer experienced in Python, "
            "PyTorch, computer vision, testing, and production deployment."
        ),
    )
    original = service.evaluator.evaluate_result
    service.evaluator.evaluate_result = lambda *args: (_ for _ in ()).throw(RuntimeError("provider down"))
    try:
        try:
            service.submit_answer(
                state["interview_id"], "I used Python.", turn_id, role="admin"
            )
        except RuntimeError:
            pass
    finally:
        service.evaluator.evaluate_result = original

    with SessionLocal() as session:
        turn = session.execute(
            select(InterviewTurnRecord).where(InterviewTurnRecord.turn_id == turn_id)
        ).scalar_one()
    assert turn.status == "failed_retryable"
