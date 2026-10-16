from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from time import sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.main import app
from apps.api.v1.routes import interview as interview_routes
from agents.interview_agent.graph import (
    InterviewAgentCore,
    InterviewQuestionPlan,
    PLANNING_CONTEXT_MAX_CHARS,
    PLANNING_CONTEXT_MAX_CHUNKS,
    QuestionPlanningError,
)
from evaluation.service import (
    AssessmentStatus,
    CompetencyAssessment,
    DeterministicEvaluator,
    EvaluationResult,
    EvaluationService,
    EvidenceItem,
    EvidenceStrength,
    SuggestedNextAction,
)
from rag.service import DocumentChunk, HybridRetriever, RAGQuestionService
from services.database import (
    InterviewAssessmentRecord,
    InterviewQuestionRecord,
    InterviewRecord,
    InterviewTurnRecord,
    SessionLocal,
    init_db,
)
from services.interview_service import InterviewService
from services.user_store import UserStore


POSITION = "AI Engineer"
JOB_DESCRIPTION = (
    "Build Python services, train PyTorch computer-vision models, deploy them with "
    "Kubernetes, and monitor production quality and latency."
)
CANDIDATE_RESUME = (
    "The candidate built Python FastAPI services, trained PyTorch image classifiers, "
    "used YOLO for object detection, and deployed workloads to Kubernetes."
)

SAMPLE_RAG_CHUNKS = [
    DocumentChunk(
        "sample-cv:candidate",
        "cv-1",
        "CV evidence: Python FastAPI, PyTorch image classification, YOLO object detection, and Kubernetes deployment.",
        source_type="cv",
        source="indexed:cv/sample_candidate.md",
    ),
    DocumentChunk(
        "sample-jd:role",
        "jd-1",
        "JD requirements: Python async services, computer vision model quality, Kubernetes, and production latency.",
        source_type="jd",
        source="indexed:jd/sample_ai_engineer.md",
    ),
    DocumentChunk(
        "sample-company:handbook",
        "company-1",
        "Company practices: least-privilege access control, incident ownership, and rollback communication.",
        source_type="company",
        source="indexed:company/sample_handbook.md",
    ),
    DocumentChunk(
        "sample-knowledge:guide",
        "knowledge-1",
        "Knowledge guide: database transaction isolation, locking, model monitoring, and service reliability.",
        source_type="knowledge",
        source="indexed:knowledge/sample_guide.md",
    ),
]

QUESTION_SPECS = [
    ("python", "How did you structure the FastAPI service?", "service design"),
    ("python", "How did you handle async cancellation?", "async reliability"),
    ("pytorch", "How did you validate the model training pipeline?", "model training"),
    ("computer_vision", "How did you measure YOLO detection quality?", "vision quality"),
    ("computer_vision", "How did you address difficult image conditions?", "vision robustness"),
    ("deployment", "How did you deploy the model with Kubernetes?", "deployment"),
    ("observability", "Which production signals exposed latency regressions?", "monitoring"),
    ("security", "How did you apply least-privilege access controls?", "secure operations"),
    ("incident_response", "How did you coordinate rollback during an incident?", "incident response"),
    ("databases", "How would transaction isolation affect concurrent writes?", "data consistency"),
]


def _plan_payload() -> dict:
    competencies = sorted({competency for competency, _, _ in QUESTION_SPECS})
    questions = []
    for index, (competency, text, objective) in enumerate(QUESTION_SPECS):
        questions.append(
            {
                "proposal": {
                    "question": text,
                    "competency": competency,
                    "difficulty": "medium",
                    "intent": objective,
                    "expected_evidence": [f"Concrete example for {objective}"],
                },
                "objective": objective,
                "rubric": {
                    "competency": competency,
                    "weak": "Names a concept but gives no example.",
                    "acceptable": "Explains a relevant action and its purpose.",
                    "strong": "Gives a specific action, trade-off, and measured result.",
                    "exceptional": "Shows ownership, deep reasoning, and reproducible impact.",
                    "requires_practical_evidence": True,
                },
            }
        )
    return {"competencies": competencies, "questions": questions}


class SamplePlanningLLM:
    provider_name = "sample"
    model = "sample-plan"
    prompt_version = "question-plan-test-v1"

    def __init__(self, response: object | None = None) -> None:
        self.response = response if response is not None else _plan_payload()
        self.calls: list[tuple[str, str, type]] = []

    def generate(self, system_instruction: str, user_content: str) -> str:
        raise AssertionError("question planning must use the structured LLM interface")

    def generate_structured(self, system_instruction: str, user_content: str, schema: type):
        self.calls.append((system_instruction, user_content, schema))
        if schema.__name__ == "QuestionProposal":
            return schema(
                question="What specific result did your actions produce?",
                competency="python",
                difficulty="medium",
                intent="Probe the missing measurable result.",
                expected_evidence=["measurable result"],
            )
        return deepcopy(self.response)


def _create_planner(
    llm: SamplePlanningLLM | None = None,
    source_types: set[str] | None = None,
) -> tuple[InterviewAgentCore, SamplePlanningLLM]:
    selected = [
        chunk for chunk in SAMPLE_RAG_CHUNKS
        if source_types is None or chunk.source_type in source_types
    ]
    rag = RAGQuestionService(HybridRetriever(documents=selected))
    interview_service = InterviewService.__new__(InterviewService)
    interview_service.rag = rag

    provider = llm or SamplePlanningLLM()
    return InterviewAgentCore(
        llm_provider=provider,
        context_retriever=interview_service._retrieve_graph_context,
    ), provider


class SampleAdaptiveEvaluator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, object]] = []

    def evaluate(self, question, answer, competency, rubric, context=None):
        self.calls.append((question, answer, competency, rubric))
        insufficient = answer.startswith("insufficient:")
        status = (
            AssessmentStatus.INSUFFICIENT_EVIDENCE
            if insufficient
            else AssessmentStatus.DEMONSTRATED
        )
        result = EvaluationResult(
            competency=competency,
            evidence=[
                EvidenceItem(
                    competency=competency,
                    text=answer,
                    strength=EvidenceStrength.WEAK if insufficient else EvidenceStrength.STRONG,
                    specificity="medium",
                    ownership="explicit",
                    relevance=1.0,
                )
            ],
            assessment=CompetencyAssessment(
                competency=competency,
                score=1 if insufficient else 4,
                status=status,
                evidence_strength=(
                    EvidenceStrength.WEAK if insufficient else EvidenceStrength.STRONG
                ),
                confidence=0.9,
                gaps=[],
                missing_evidence=["measurable result"] if insufficient else [],
                rationale="Sample evidence-based assessment.",
                next_action=(
                    SuggestedNextAction.DIG_DEEPER
                    if insufficient
                    else SuggestedNextAction.CHANGE_COMPETENCY
                ),
                evaluator_type="sample",
                evaluator_version="adaptive-test-v1",
            ),
            position=POSITION,
        )
        return result


def _configure_adaptive_service(monkeypatch, evaluator: SampleAdaptiveEvaluator):
    service = interview_routes.service
    llm = SamplePlanningLLM()
    rag = RAGQuestionService(HybridRetriever(documents=SAMPLE_RAG_CHUNKS))
    agent = InterviewAgentCore(
        llm_provider=llm,
        context_retriever=service._retrieve_graph_context,
    )
    monkeypatch.setattr(service, "rag", rag)
    monkeypatch.setattr(service, "agent", agent)
    monkeypatch.setattr(service, "evaluator", EvaluationService(evaluator))

    class TestLock:
        def release(self):
            return True

    monkeypatch.setattr(service, "_get_processing_lock", lambda _interview_id: TestLock())
    return service, llm


def test_question_plan_has_ten_distinct_questions_with_rubrics_and_rag_context():
    agent, llm = _create_planner()

    plan = agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)

    assert len(plan.questions) == 10
    assert len({item.proposal.question.casefold() for item in plan.questions}) == 10
    assert len({item.objective.casefold() for item in plan.questions}) == 10
    assert all(item.proposal.competency in plan.competencies for item in plan.questions)
    assert all(item.rubric.competency == item.proposal.competency for item in plan.questions)
    assert all(item.objective.strip() and item.rubric.strong.strip() for item in plan.questions)

    competency_set = {item.proposal.competency for item in plan.questions}
    assert {"python", "pytorch", "computer_vision", "deployment"} <= competency_set
    prompt = llm.calls[0][1]
    assert llm.calls[0][2] is InterviewQuestionPlan
    assert POSITION in prompt and JOB_DESCRIPTION in prompt and CANDIDATE_RESUME in prompt
    assert any("YOLO" in item.proposal.question for item in plan.questions)
    assert any("Kubernetes" in item.proposal.question for item in plan.questions)
    for chunk in SAMPLE_RAG_CHUNKS:
        source_label = f"UNTRUSTED_RETRIEVED_CONTEXT_{chunk.source_type.upper()}:\n"
        section = prompt.split(source_label, 1)[1].split(
            "\n\nUNTRUSTED_RETRIEVED_CONTEXT_", 1
        )[0]
        assert chunk.text in section
        assert all(
            other.text not in section
            for other in SAMPLE_RAG_CHUNKS
            if other.source_type != chunk.source_type
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["questions"].pop(),
        lambda payload: payload["questions"][1]["proposal"].update(
            {"question": payload["questions"][0]["proposal"]["question"]}
        ),
        lambda payload: payload["questions"][0]["rubric"].update(
            {"competency": "different_competency"}
        ),
        lambda payload: payload["questions"][0].pop("objective"),
        lambda payload: payload["questions"][0]["proposal"].update(
            {"competency": "unlisted_competency"}
        ),
    ],
    ids=("missing-question", "duplicate-question", "rubric-mismatch", "missing-objective", "unlinked-competency"),
)
def test_invalid_question_plan_is_rejected(mutate):
    payload = _plan_payload()
    mutate(payload)
    agent, _ = _create_planner(SamplePlanningLLM(payload))

    with pytest.raises(QuestionPlanningError, match="valid ten-question plan"):
        agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)


@pytest.mark.parametrize(
    ("position", "job_description", "candidate_resume"),
    [
        ("", JOB_DESCRIPTION, CANDIDATE_RESUME),
        (POSITION, "  ", CANDIDATE_RESUME),
    ],
    ids=("missing-position", "missing-jd"),
)
def test_missing_required_inputs_fail_before_calling_llm(position, job_description, candidate_resume):
    agent, llm = _create_planner()

    with pytest.raises(QuestionPlanningError, match="requires non-empty"):
        agent.plan_questions(position, job_description, candidate_resume)

    assert llm.calls == []


@pytest.mark.parametrize("missing_source", ("cv", "jd", "company", "knowledge"))
def test_question_plan_continues_when_optional_rag_source_is_missing(missing_source):
    source_types = {"cv", "jd", "company", "knowledge"} - {missing_source}
    agent, llm = _create_planner(source_types=source_types)

    plan = agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)

    assert len(plan.questions) == 10
    assert len(llm.calls) == 1
    labels = {
        "cv": "UNTRUSTED_RETRIEVED_CONTEXT_CV:\n",
        "jd": "UNTRUSTED_RETRIEVED_CONTEXT_JD:\n",
        "company": "UNTRUSTED_RETRIEVED_CONTEXT_COMPANY:\n",
        "knowledge": "UNTRUSTED_RETRIEVED_CONTEXT_KNOWLEDGE:\n",
    }
    section = llm.calls[0][1].split(labels[missing_source], 1)[1].split(
        "\n\nUNTRUSTED_RETRIEVED_CONTEXT_", 1
    )[0]
    assert "[unavailable]" in section


def test_question_plan_preserves_all_attributed_sources_with_compact_context():
    agent, llm = _create_planner()

    plan = agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)

    assert len(plan.questions) == 10
    user_content = llm.calls[0][1]
    for label, source in (
        ("CV", "cv"),
        ("JD", "jd"),
        ("COMPANY", "company"),
        ("KNOWLEDGE", "knowledge"),
    ):
        section = user_content.split(
            f"UNTRUSTED_RETRIEVED_CONTEXT_{label}:\n", 1
        )[1].split("\n\nUNTRUSTED_RETRIEVED_CONTEXT_", 1)[0]
        assert f"[UNTRUSTED_CONTEXT source=sample-{source}:" in section
        assert len(section) <= PLANNING_CONTEXT_MAX_CHARS


def test_planning_context_keeps_at_most_two_complete_attributions_and_caps_length():
    context = (
        "[LEXICAL_ONLY]\n"
        "[UNTRUSTED_CONTEXT source=cv:one chunk=1] "
        + ("A" * 700)
        + "\n[UNTRUSTED_CONTEXT source=cv:two chunk=2] second chunk\n"
        + "[UNTRUSTED_CONTEXT source=cv:three chunk=3] third chunk"
    )

    compacted = InterviewAgentCore._compact_planning_context(context)

    assert len(compacted) <= PLANNING_CONTEXT_MAX_CHARS
    assert compacted.startswith("[LEXICAL_ONLY]\n[UNTRUSTED_CONTEXT source=cv:one chunk=1]")
    assert compacted.count("[UNTRUSTED_CONTEXT ") <= PLANNING_CONTEXT_MAX_CHUNKS
    assert compacted.count("[UNTRUSTED_CONTEXT ") == 1
    assert compacted.endswith("...")


def test_malformed_structured_llm_output_is_reported():
    agent, _ = _create_planner(SamplePlanningLLM("not a structured plan"))

    with pytest.raises(QuestionPlanningError, match="valid ten-question plan"):
        agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)


def test_question_planning_requires_llm_but_not_rag():
    with pytest.raises(QuestionPlanningError, match="structured LLM provider"):
        InterviewAgentCore().plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)

    # A configured structured LLM is enough to produce the JD-first base plan.
    agent = InterviewAgentCore(llm_provider=SamplePlanningLLM())
    plan = agent.plan_questions(POSITION, JOB_DESCRIPTION, CANDIDATE_RESUME)
    assert len(plan.questions) == 10


def test_candidate_resume_is_optional_for_question_planning():
    agent, llm = _create_planner()
    plan = agent.plan_questions(POSITION, JOB_DESCRIPTION, "")

    assert len(plan.questions) == 10
    assert len(llm.calls) == 1
    assert "[CV not provided]" in llm.calls[0][1]


def test_start_endpoint_persists_plan_and_retries_same_session_without_regeneration(
    monkeypatch,
):
    service, llm = _configure_adaptive_service(
        monkeypatch, SampleAdaptiveEvaluator()
    )

    email = f"question-plan-{uuid4()}@example.test"
    password = "sample-test-password"
    user = UserStore.create(email, password, role="admin")
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        payload = {
            "candidate_id": "sample-candidate",
            "position": POSITION,
            "job_description": JOB_DESCRIPTION,
            "candidate_resume": CANDIDATE_RESUME,
            "idempotency_key": f"plan-start-{uuid4()}",
        }

        started = client.post(
            "/api/v1/interview/start", json=payload, headers=headers
        )
        assert started.status_code == 200, started.text
        started_state = started.json()
        interview_id = started_state["interview_id"]
        plan = started_state["question_plan"]
        assert len(plan["questions"]) == 10
        assert started_state["current_question"] == plan["questions"][0]["proposal"]["question"]
        assert started_state["current_competency"] == plan["questions"][0]["proposal"]["competency"]
        assert started_state["interview_plan"]["competencies"] == plan["competencies"]
        assert "start_request_hash" not in started_state

        with SessionLocal() as session:
            persisted = session.get(InterviewRecord, interview_id)
            initial_question = session.execute(
                select(InterviewQuestionRecord).where(
                    InterviewQuestionRecord.interview_id == interview_id
                )
            ).scalar_one()
            assert persisted is not None
            assert persisted.start_request_key == payload["idempotency_key"]
            assert persisted.start_request_hash
            assert persisted.current_question == plan["questions"][0]["proposal"]["question"]
            assert initial_question.sequence_number == 1
            assert initial_question.question_text == persisted.current_question
            assert initial_question.competency == plan["questions"][0]["proposal"]["competency"]

        retried_start = client.post(
            "/api/v1/interview/start", json=payload, headers=headers
        )
        assert retried_start.status_code == 200
        assert retried_start.json()["interview_id"] == interview_id
        assert retried_start.json()["question_plan"] == plan
        assert len(llm.calls) == 1

        answer_request = {
            "turn_id": f"plan-answer-{uuid4()}",
            "answer": "I used Python FastAPI and measured request latency.",
        }
        answer_url = f"/api/v1/interview/{interview_id}/answer"
        first_answer = client.post(answer_url, json=answer_request, headers=headers)
        repeated_answer = client.post(answer_url, json=answer_request, headers=headers)
        assert first_answer.status_code == 200, first_answer.text
        assert repeated_answer.status_code == 200, repeated_answer.text
        assert first_answer.json()["current_question"] == plan["questions"][1]["proposal"]["question"]
        assert repeated_answer.json()["current_question"] == first_answer.json()["current_question"]
        assert len(llm.calls) == 1

        with SessionLocal() as session:
            persisted_questions = session.execute(
                select(InterviewQuestionRecord)
                .where(InterviewQuestionRecord.interview_id == interview_id)
                .order_by(InterviewQuestionRecord.sequence_number)
            ).scalars().all()
            sessions_for_key = session.execute(
                select(InterviewRecord).where(
                    InterviewRecord.start_request_key == payload["idempotency_key"]
                )
            ).scalars().all()
        assert [item.question_text for item in persisted_questions] == [
            plan["questions"][0]["proposal"]["question"],
            plan["questions"][1]["proposal"]["question"],
        ]
        assert len(sessions_for_key) == 1

        changed_request = {**payload, "job_description": f"{JOB_DESCRIPTION} New requirement."}
        conflict = client.post(
            "/api/v1/interview/start", json=changed_request, headers=headers
        )
        assert conflict.status_code == 409
        assert len(llm.calls) == 1
        assert user["role"] == "admin"


def test_start_endpoint_keeps_legacy_request_and_validates_paired_plan_inputs(
    monkeypatch,
):
    service = interview_routes.service
    llm = SamplePlanningLLM()
    monkeypatch.setattr(
        service,
        "agent",
        InterviewAgentCore(llm_provider=llm, context_retriever=service._retrieve_graph_context),
    )
    monkeypatch.setattr(
        service,
        "rag",
        RAGQuestionService(HybridRetriever(documents=SAMPLE_RAG_CHUNKS)),
    )
    email = f"question-plan-legacy-{uuid4()}@example.test"
    password = "sample-test-password"
    UserStore.create(email, password, role="admin")

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        # JD is required for the new JD-first planning flow. Reject requests that
        # omit it as a client validation error rather than returning a server error.
        missing_jd = client.post(
            "/api/v1/interview/start",
            json={"candidate_id": "legacy-candidate", "position": POSITION},
            headers=headers,
        )
        assert missing_jd.status_code == 422
        assert llm.calls == []

        # CV is optional: a valid JD alone must be enough to create the plan.
        jd_only = client.post(
            "/api/v1/interview/start",
            json={
                "candidate_id": "sample-candidate",
                "position": POSITION,
                "job_description": JOB_DESCRIPTION,
            },
            headers=headers,
        )
        assert jd_only.status_code == 200, jd_only.text
        assert len(jd_only.json()["question_plan"]["questions"]) == 10
        assert len(llm.calls) == 1


def test_concurrent_start_with_same_key_runs_planner_once_and_returns_same_session():
    class BlockingPlanningLLM(SamplePlanningLLM):
        def __init__(self):
            super().__init__()
            self.started = Event()
            self.release = Event()

        def generate_structured(self, system_instruction: str, user_content: str, schema: type):
            self.calls.append((system_instruction, user_content, schema))
            self.started.set()
            if not self.release.wait(timeout=10):
                raise TimeoutError("sample planner wait timed out")
            return deepcopy(self.response)

    init_db()
    llm = BlockingPlanningLLM()
    rag = RAGQuestionService(HybridRetriever(documents=SAMPLE_RAG_CHUNKS))
    service = InterviewService(rag=rag)
    service.agent = InterviewAgentCore(
        llm_provider=llm,
        context_retriever=service._retrieve_graph_context,
    )
    request = {
        "candidate_id": "concurrent-sample-candidate",
        "position": POSITION,
        "mode": "text",
        "owner_role": "admin",
        "job_description": JOB_DESCRIPTION,
        "candidate_resume": CANDIDATE_RESUME,
        "idempotency_key": f"concurrent-plan-start-{uuid4()}",
    }

    def start():
        return service.start_interview(**request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(start)
        assert llm.started.wait(timeout=5)
        second = executor.submit(start)
        try:
            sleep(0.15)
            assert len(llm.calls) == 1
        finally:
            llm.release.set()

        first_state = first.result(timeout=10)
        second_state = second.result(timeout=10)

    assert first_state["interview_id"] == second_state["interview_id"]
    assert first_state["question_plan"] == second_state["question_plan"]
    assert len(llm.calls) == 1
    with SessionLocal() as session:
        records = session.execute(
            select(InterviewRecord).where(
                InterviewRecord.start_request_key == request["idempotency_key"]
            )
        ).scalars().all()
        questions = session.execute(
            select(InterviewQuestionRecord).where(
                InterviewQuestionRecord.interview_id == first_state["interview_id"]
            )
        ).scalars().all()
    assert len(records) == 1
    assert records[0].start_request_status == "complete"
    assert len(questions) == 1


def test_planned_interview_answers_follow_saved_plan_retry_once_and_finish(
    monkeypatch,
):
    init_db()
    service = interview_routes.service
    llm = SamplePlanningLLM()
    rag = RAGQuestionService(HybridRetriever(documents=SAMPLE_RAG_CHUNKS))
    agent = InterviewAgentCore(
        llm_provider=llm,
        context_retriever=service._retrieve_graph_context,
    )
    monkeypatch.setattr(service, "rag", rag)
    monkeypatch.setattr(service, "agent", agent)
    monkeypatch.setattr(
        service,
        "evaluator",
        EvaluationService(DeterministicEvaluator()),
    )

    class TestLock:
        def release(self):
            return True

    monkeypatch.setattr(service, "_get_processing_lock", lambda _interview_id: TestLock())

    email = f"planned-interview-{uuid4()}@example.test"
    password = "sample-test-password"
    UserStore.create(email, password, role="admin")
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        started = client.post(
            "/api/v1/interview/start",
            json={
                "candidate_id": "sample-task4-candidate",
                "position": POSITION,
                "job_description": JOB_DESCRIPTION,
                "candidate_resume": CANDIDATE_RESUME,
                "idempotency_key": f"task4-plan-{uuid4()}",
            },
            headers=headers,
        )
        assert started.status_code == 200, started.text
        initial = started.json()
        interview_id = initial["interview_id"]
        plan = initial["question_plan"]
        assert initial["current_question"] == plan["questions"][0]["proposal"]["question"]

        for index in range(10):
            answer = (
                f"I built and deployed a Python PyTorch object detection service; "
                f"latency was reduced by 20% for planned question {index + 1}."
            )
            request = {
                "turn_id": f"task4-turn-{uuid4()}",
                "answer": answer,
            }
            response = client.post(
                f"/api/v1/interview/{interview_id}/answer",
                json=request,
                headers=headers,
            )
            assert response.status_code == 200, response.text
            state = response.json()
            assert len(state["history"]) == index + 1
            assert state["history"][-1]["answer"] == answer

            if index < 9:
                assert state["current_question"] == plan["questions"][index + 1]["proposal"]["question"]
                assert state["status"] == "active"
            else:
                assert state["status"] == "completed"
                assert state["current_question"] == plan["questions"][-1]["proposal"]["question"]

            if index == 4:
                replay = client.post(
                    f"/api/v1/interview/{interview_id}/answer",
                    json=request,
                    headers=headers,
                )
                assert replay.status_code == 200, replay.text
                assert replay.json()["history"] == state["history"]

        assert len(llm.calls) == 1

        finished_replay = client.post(
            f"/api/v1/interview/{interview_id}/answer",
            json=request,
            headers=headers,
        )
        assert finished_replay.status_code == 200
        assert finished_replay.json()["status"] == "completed"
        assert len(llm.calls) == 1

        with SessionLocal() as session:
            turns = session.execute(
                select(InterviewTurnRecord)
                .where(InterviewTurnRecord.interview_id == interview_id)
                .order_by(InterviewTurnRecord.sequence_number)
            ).scalars().all()
            questions = session.execute(
                select(InterviewQuestionRecord)
                .where(InterviewQuestionRecord.interview_id == interview_id)
                .order_by(InterviewQuestionRecord.sequence_number)
            ).scalars().all()

        assert len(turns) == len(questions) == 10
        assert [turn.sequence_number for turn in turns] == list(range(1, 11))
        assert [question.sequence_number for question in questions] == list(range(1, 11))
        assert all(turn.status == "completed" for turn in turns)
        assert all(
            turn.question_id == questions[index].id
            and turn.candidate_answer
            == (
                f"I built and deployed a Python PyTorch object detection service; "
                f"latency was reduced by 20% for planned question {index + 1}."
            )
            for index, turn in enumerate(turns)
        )


def test_adaptive_follow_up_is_single_persisted_and_retry_safe(monkeypatch, tmp_path):
    init_db()
    evaluator = SampleAdaptiveEvaluator()
    _, llm = _configure_adaptive_service(monkeypatch, evaluator)
    monkeypatch.setattr(interview_routes.report_service, "output_dir", tmp_path)
    email = f"task5-followup-{uuid4()}@example.test"
    UserStore.create(email, "sample-test-password", role="admin")

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "sample-test-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        started = client.post(
            "/api/v1/interview/start",
            json={
                "candidate_id": f"sample-task5-{uuid4()}",
                "position": POSITION,
                "job_description": JOB_DESCRIPTION,
                "candidate_resume": CANDIDATE_RESUME,
                "idempotency_key": f"task5-followup-{uuid4()}",
            },
            headers=headers,
        )
        assert started.status_code == 200, started.text
        initial = started.json()
        interview_id = initial["interview_id"]
        first_question = initial["current_question"]

        weak_turn = {"turn_id": f"task5-weak-{uuid4()}", "answer": "insufficient: I helped."}
        weak_response = client.post(
            f"/api/v1/interview/{interview_id}/answer",
            json=weak_turn,
            headers=headers,
        )
        assert weak_response.status_code == 200, weak_response.text
        weak_state = weak_response.json()
        assert weak_state["awaiting_follow_up"] is True
        assert weak_state["planned_question_index"] == 0
        assert weak_state["follow_up_state"] == {"0": "pending"}
        assert weak_state["current_question"] == "What specific result did your actions produce?"
        assert weak_state["status"] == "active"
        expected_rubric = initial["question_plan"]["questions"][0]["rubric"]
        assert evaluator.calls[0][3].model_dump(mode="json") == expected_rubric

        replay = client.post(
            f"/api/v1/interview/{interview_id}/answer",
            json=weak_turn,
            headers=headers,
        )
        assert replay.status_code == 200
        assert replay.json()["history"] == weak_state["history"]
        assert len(evaluator.calls) == 1
        assert len([call for call in llm.calls if call[2].__name__ == "QuestionProposal"]) == 1

        follow_up_turn = {
            "turn_id": f"task5-followup-answer-{uuid4()}",
            "answer": "insufficient: I tried a change, but did not measure an outcome.",
        }
        follow_up_response = client.post(
            f"/api/v1/interview/{interview_id}/answer",
            json=follow_up_turn,
            headers=headers,
        )
        assert follow_up_response.status_code == 200, follow_up_response.text
        completed_state = follow_up_response.json()
        assert completed_state["awaiting_follow_up"] is False
        assert completed_state["planned_question_index"] == 1
        assert completed_state["follow_up_state"] == {"0": "completed"}
        assert completed_state["current_question"] == completed_state["question_plan"]["questions"][1]["proposal"]["question"]
        assert len(evaluator.calls) == 2
        assert [call[2] for call in evaluator.calls] == ["python", "python"]
        assert all(
            call[3].model_dump(mode="json") == expected_rubric
            for call in evaluator.calls
        )
        assert evaluator.calls[0][0] == first_question
        assert evaluator.calls[1][0] == weak_state["current_question"]
        assert [call[2].__name__ for call in llm.calls].count("QuestionProposal") == 1
        persisted_state = client.get(
            f"/api/v1/interview/{interview_id}",
            headers=headers,
        )
        assert persisted_state.status_code == 200
        assert persisted_state.json()["follow_up_state"] == {"0": "completed"}
        exported = client.post(
            f"/api/v1/interview/{interview_id}/report",
            params={"format": "json"},
            headers=headers,
        )
        assert exported.status_code == 200, exported.text
        report = exported.json()["report"]
        reported_assessment = report["competencies"]["python"]["question_assessments"][1]
        assert reported_assessment["is_follow_up"] is True
        assert reported_assessment["rubric"] == expected_rubric
        assert reported_assessment["answer_quote"] == follow_up_turn["answer"]
        assert reported_assessment["follow_up_status"] == "completed"
        assert report["follow_up_results"][0]["follow_up_answer"] == follow_up_turn["answer"]

        with SessionLocal() as session:
            turns = session.execute(
                select(InterviewTurnRecord)
                .where(InterviewTurnRecord.interview_id == interview_id)
                .order_by(InterviewTurnRecord.sequence_number)
            ).scalars().all()
            questions = session.execute(
                select(InterviewQuestionRecord)
                .where(InterviewQuestionRecord.interview_id == interview_id)
                .order_by(InterviewQuestionRecord.sequence_number)
            ).scalars().all()
            assessments = session.execute(
                select(InterviewAssessmentRecord).where(
                    InterviewAssessmentRecord.interview_id == interview_id
                )
            ).scalars().all()

        assert len(turns) == len(assessments) == 2
        assert len(questions) == 3
        assert turns[0].question_id == questions[0].id
        assert turns[1].question_id == questions[1].id
        assert {assessment.competency for assessment in assessments} == {"python"}


def test_sufficient_sample_answer_advances_without_follow_up(monkeypatch):
    init_db()
    evaluator = SampleAdaptiveEvaluator()
    _configure_adaptive_service(monkeypatch, evaluator)
    email = f"task5-sufficient-{uuid4()}@example.test"
    UserStore.create(email, "sample-test-password", role="admin")

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "sample-test-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        started = client.post(
            "/api/v1/interview/start",
            json={
                "candidate_id": f"sample-task5-{uuid4()}",
                "position": POSITION,
                "job_description": JOB_DESCRIPTION,
                "candidate_resume": CANDIDATE_RESUME,
                "idempotency_key": f"task5-sufficient-{uuid4()}",
            },
            headers=headers,
        )
        assert started.status_code == 200, started.text
        initial = started.json()
        response = client.post(
            f"/api/v1/interview/{initial['interview_id']}/answer",
            json={
                "turn_id": f"task5-sufficient-turn-{uuid4()}",
                "answer": "I built the service and measured a 30% latency reduction.",
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        state = response.json()
        assert state["awaiting_follow_up"] is False
        assert state["planned_question_index"] == 1
        assert state["follow_up_state"] == {"0": "not_required"}
        assert state["current_question"] == state["question_plan"]["questions"][1]["proposal"]["question"]
        assert len(evaluator.calls) == 1
