from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api import main as api_main
from apps.api.main import app
from apps.api.v1.routes.interview import service as interview_service
from agents.interview_agent.graph import QuestionPlanningError
from integrations.llm_providers.provider import LLMTimeoutError
from services.database import InterviewQuestionRecord, InterviewTurnRecord, SessionLocal
from services.interview_service import InterviewProcessingError
from services.user_store import UserStore

TEST_ADMIN_EMAIL = "api-test-admin@example.test"
TEST_ADMIN_PASSWORD = "api-test-only-password"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        UserStore.create(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, role="admin")
        yield test_client


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_start_interview_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-100", "position": "AI Engineer", "mode": "text"},
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "candidate-100"
    assert payload["position"] == "AI Engineer"
    assert "introduce" in payload["current_question"].lower()


def test_start_interview_maps_question_planning_error_to_503(client, monkeypatch):
    def fail_planning(*args, **kwargs):
        raise QuestionPlanningError("synthetic planner failure")

    monkeypatch.setattr(interview_service, "start_interview", fail_planning)
    response = client.post(
        "/api/v1/interview/start",
        json={
            "candidate_id": "candidate-planning-error",
            "position": "AI Engineer",
            "job_description": "Synthetic job description.",
            "candidate_resume": "Synthetic candidate resume.",
        },
        headers=auth_headers(client),
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Interview question planning is temporarily unavailable"
    }


def test_submit_answer_endpoint_updates_state_and_scores(client: TestClient):
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-200", "position": "AI Engineer", "mode": "text"},
        headers=auth_headers(client),
    )
    interview_id = start.json()["interview_id"]

    response = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={
            "turn_id": "turn-api-1",
            "answer": (
                "I have worked with Python, PyTorch, and YOLOv8 for computer vision. "
                "I also deployed a model to production and optimized inference latency."
            ),
        },
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skills"]["general"]["score"] >= 3
    assert payload["evaluation"]["assessment"]["competency"] == "general"
    assert payload["overall_score"] >= 0


def test_duplicate_turn_id_replays_without_appending_history(client: TestClient):
    headers = auth_headers(client)
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-idempotent", "position": "AI Engineer", "mode": "text"},
        headers=headers,
    )
    interview_id = start.json()["interview_id"]
    request = {
        "turn_id": "turn-duplicate-1",
        "answer": "I deployed a Python service to production.",
    }

    first = client.post(f"/api/v1/interview/{interview_id}/answer", json=request, headers=headers)
    second = client.post(f"/api/v1/interview/{interview_id}/answer", json=request, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["history"]) == 1
    assert second.json()["history"] == first.json()["history"]


def test_adaptive_graph_result_and_answered_question_are_persisted(client: TestClient):
    headers = auth_headers(client)
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-graph-state", "position": "AI Engineer"},
        headers=headers,
    )
    interview_id = start.json()["interview_id"]
    first_question = start.json()["current_question"]
    turn_id = f"turn-graph-state-{uuid4()}"

    response = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": turn_id, "answer": "I deployed a Python service."},
        headers=headers,
    )

    assert response.status_code == 200
    state = response.json()
    assert state["evaluation"]["assessment"]["competency"] == "general"
    assert state["next_action"] == state["recommended_next_action"]
    assert state["current_question"] != first_question
    persisted = client.get(f"/api/v1/interview/{interview_id}", headers=headers).json()
    assert persisted["current_question"] == state["current_question"]
    assert persisted["evaluation"] == state["evaluation"]

    with SessionLocal() as session:
        turn = session.execute(
            select(InterviewTurnRecord).where(
                InterviewTurnRecord.interview_id == interview_id,
                InterviewTurnRecord.turn_id == turn_id,
            )
        ).scalar_one()
        questions = session.execute(
            select(InterviewQuestionRecord)
            .where(InterviewQuestionRecord.interview_id == interview_id)
            .order_by(InterviewQuestionRecord.sequence_number)
        ).scalars().all()
    assert turn.status == "completed"
    assert turn.question_id == questions[0].id
    assert len(questions) == 2
    assert questions[1].question_text == state["current_question"]


def test_interview_endpoints_require_authentication(client: TestClient):
    response = client.get("/api/v1/interviews")
    assert response.status_code == 401


def test_evaluation_provider_failure_returns_retryable_service_error(client: TestClient, monkeypatch):
    headers = auth_headers(client)
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-evaluation-retry", "position": "AI Engineer"},
        headers=headers,
    )
    interview_id = start.json()["interview_id"]
    request = {"turn_id": "turn-evaluation-retry", "answer": "I implemented a Python API."}
    original_evaluate = interview_service.evaluator.evaluate_result
    monkeypatch.setattr(
        interview_service.evaluator,
        "evaluate_result",
        lambda *args: (_ for _ in ()).throw(LLMTimeoutError("provider timed out")),
    )

    failed = client.post(f"/api/v1/interview/{interview_id}/answer", json=request, headers=headers)
    assert failed.status_code == 503
    assert "same turn_id" in failed.json()["detail"]

    monkeypatch.setattr(interview_service.evaluator, "evaluate_result", original_evaluate)
    retry = client.post(f"/api/v1/interview/{interview_id}/answer", json=request, headers=headers)
    assert retry.status_code == 200


def test_processing_duplicate_returns_retryable_conflict(client: TestClient, monkeypatch):
    headers = auth_headers(client)
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": "candidate-processing", "position": "AI Engineer"},
        headers=headers,
    )
    interview_id = start.json()["interview_id"]
    monkeypatch.setattr(
        interview_service,
        "submit_answer",
        lambda *args: (_ for _ in ()).throw(
            InterviewProcessingError("Interview is still processing; retry the same turn_id and answer.")
        ),
    )

    response = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json={"turn_id": "turn-processing", "answer": "I used Python."},
        headers=headers,
    )

    assert response.status_code == 409
    assert "still processing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_production_startup_skips_development_database_and_admin_bootstrap(monkeypatch):
    class RedisClientStub:
        _client = None

        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(api_main.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(api_main.settings, "SECRET_KEY", "production-test-secret-key-that-is-long-enough")
    monkeypatch.setattr(api_main.settings, "ENABLE_DEV_ADMIN_BOOTSTRAP", False)
    monkeypatch.setattr(api_main, "RedisClient", RedisClientStub)
    monkeypatch.setattr(api_main, "init_db", lambda: pytest.fail("production must use migrations"))
    monkeypatch.setattr(
        api_main.UserStore,
        "ensure_default_admin",
        lambda *args, **kwargs: pytest.fail("production must not seed a default admin"),
    )

    async with api_main.lifespan(app):
        pass


def test_production_security_requires_private_secret_and_disabled_bootstrap(monkeypatch):
    monkeypatch.setattr(api_main.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(api_main.settings, "SECRET_KEY", "your-secret-key-change-in-production")
    monkeypatch.setattr(api_main.settings, "ENABLE_DEV_ADMIN_BOOTSTRAP", False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        api_main.validate_production_security()

    monkeypatch.setattr(api_main.settings, "SECRET_KEY", "production-test-secret-key-that-is-long-enough")
    monkeypatch.setattr(api_main.settings, "ENABLE_DEV_ADMIN_BOOTSTRAP", True)
    with pytest.raises(RuntimeError, match="BOOTSTRAP"):
        api_main.validate_production_security()
