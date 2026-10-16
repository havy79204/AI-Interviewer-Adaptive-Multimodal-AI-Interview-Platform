from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from agents.interview_agent.graph import AnswerAnalysis, InterviewAgentCore, InterviewQuestionPlan
from apps.api import main as api_main
from apps.api.main import app
from apps.api.v1.routes import interview as interview_routes
from evaluation.service import (
    AssessmentStatus,
    CompetencyAssessment,
    EvaluationResult,
    EvaluationService,
    EvidenceItem,
    EvidenceStrength,
    SuggestedNextAction,
)
from rag.chunking import extract_with_docling, run_indexing
from rag.ingest import ingest_runtime_corpus
from rag.service import (
    DenseRetriever,
    HybridRetriever,
    RAGQuestionService,
    SQLAlchemyVectorStore,
)
from services.database import (
    InterviewAssessmentRecord,
    InterviewQuestionRecord,
    InterviewRecord,
    InterviewTurnRecord,
    SessionLocal,
    init_db,
)
from services.report_service import ReportService
from services.user_store import UserStore


SAMPLE_MARKDOWN = {
    "cv": (
        "# [CV 01]\n**ỨNG VIÊN: SAMPLE CANDIDATE**\n"
        "Python FastAPI engineer. CV_SAMPLE_EVIDENCE_731 built reliable APIs."
    ),
    "jd": (
        "# [JD 01]: Sample AI Engineer\n"
        "Python and PostgreSQL are required. JD_SAMPLE_REQUIREMENT_842."
    ),
    "company": (
        "# [DOC 01]: Sample Company\n"
        "Company values ownership and secure operations. COMPANY_SAMPLE_VALUE_953."
    ),
    "knowledge": (
        "# [TÀI LIỆU 01]: Sample Interview Guide\n"
        "Use measured outcomes and evidence-based questions. KNOWLEDGE_SAMPLE_GUIDE_164."
    ),
}

SOURCE_MARKERS = {
    "cv": "CV_SAMPLE_EVIDENCE_731",
    "jd": "JD_SAMPLE_REQUIREMENT_842",
    "company": "COMPANY_SAMPLE_VALUE_953",
    "knowledge": "KNOWLEDGE_SAMPLE_GUIDE_164",
}

QUESTION_SPECS = [
    ("python", "How did you structure the Python API?", "API structure"),
    ("databases", "How did you protect PostgreSQL writes?", "database safety"),
    ("security", "How did you secure the service?", "secure service"),
    ("communication", "How did you explain a technical decision?", "communication"),
    ("ownership", "How did you take ownership of a delivery?", "ownership"),
    ("reliability", "How did you improve service reliability?", "reliability"),
    ("testing", "How did you validate a risky change?", "testing"),
    ("collaboration", "How did you resolve a team disagreement?", "collaboration"),
    ("problem_solving", "How did you debug a production issue?", "problem solving"),
    ("learning", "How did you learn an unfamiliar technology?", "learning"),
]

POSITION = "Sample AI Engineer"


def _question_plan_payload() -> dict:
    competencies = [competency for competency, _, _ in QUESTION_SPECS]
    return {
        "competencies": competencies,
        "questions": [
            {
                "proposal": {
                    "question": question,
                    "competency": competency,
                    "difficulty": "medium",
                    "intent": objective,
                    "expected_evidence": [f"Specific example of {objective}"],
                },
                "objective": objective,
                "rubric": {
                    "competency": competency,
                    "weak": "Gives a claim without a concrete example.",
                    "acceptable": "Explains a relevant action and its purpose.",
                    "strong": "Provides a specific action, trade-off, and result.",
                    "exceptional": "Shows ownership and reproducible impact.",
                    "requires_practical_evidence": True,
                },
            }
            for competency, question, objective in QUESTION_SPECS
        ],
    }


class FakeDoclingConverter:
    def convert(self, source: str) -> SimpleNamespace:
        category = Path(source).parent.name
        return SimpleNamespace(
            document=SimpleNamespace(
                export_to_markdown=lambda: SAMPLE_MARKDOWN[category]
            )
        )


class SamplePipelineLLM:
    provider_name = "sample"
    model = "task7-sample"
    prompt_version = "task7-sample-v1"

    def __init__(self) -> None:
        self.plan_prompts: list[str] = []
        self.follow_up_calls = 0

    def generate(self, _system_instruction: str, _user_content: str) -> str:
        raise AssertionError("The integration must use structured mock responses.")

    def generate_structured(
        self, _system_instruction: str, user_content: str, schema: type
    ):
        if schema is InterviewQuestionPlan:
            self.plan_prompts.append(user_content)
            return deepcopy(_question_plan_payload())
        if schema is AnswerAnalysis:
            return schema(
                competencies=["python"],
                evidence=["sample response evidence"],
                evidence_strength="strong",
                gaps=[],
            )
        if schema.__name__ == "QuestionProposal":
            self.follow_up_calls += 1
            return schema(
                question="What measurable result did that Python API change produce?",
                competency="python",
                difficulty="medium",
                intent="Clarify the missing result.",
                expected_evidence=["measurable result"],
            )
        raise AssertionError(f"Unexpected structured LLM schema: {schema.__name__}")


class SampleAdaptiveEvaluator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, object]] = []

    def evaluate(self, question, answer, competency, rubric, context=None):
        del context
        self.calls.append((question, answer, competency, rubric))
        insufficient = answer.startswith("weak:")
        status = (
            AssessmentStatus.INSUFFICIENT_EVIDENCE
            if insufficient
            else AssessmentStatus.DEMONSTRATED
        )
        assessment = CompetencyAssessment(
            competency=competency,
            score=1 if insufficient else 4,
            status=status,
            evidence_strength=EvidenceStrength.WEAK if insufficient else EvidenceStrength.STRONG,
            confidence=0.9,
            gaps=["No measured result was given"] if insufficient else [],
            missing_evidence=["measurable result"] if insufficient else [],
            rationale="Sample assessment grounded in the submitted answer.",
            next_action=(
                SuggestedNextAction.DIG_DEEPER
                if insufficient
                else SuggestedNextAction.CHANGE_COMPETENCY
            ),
            evaluator_type="sample",
            evaluator_version="task7-sample-v1",
        )
        return EvaluationResult(
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
            assessment=assessment,
            position=POSITION,
        )


def _create_sample_pdfs(origin: Path) -> None:
    for category in SAMPLE_MARKDOWN:
        folder = origin / category
        folder.mkdir(parents=True)
        (folder / f"{category}_sample.pdf").write_bytes(b"sample-only; fake converter used")


def _sample_indexing_llm(_system_prompt: str, user_prompt: str, schema: type):
    line_numbers = [
        int(number)
        for number in re.findall(r"^\[L(\d+)\]", user_prompt, flags=re.MULTILINE)
    ]
    assert line_numbers, "indexing prompt must contain source line numbers"
    chunk_model = schema.model_fields["chunks"].annotation.__args__[0]
    chunk = chunk_model(start_line=min(line_numbers), end_line=max(line_numbers))
    return schema(chunks=[chunk])


def test_sample_data_runs_from_extraction_through_persisted_hr_report(
    tmp_path, monkeypatch
):
    init_db()

    origin = tmp_path / "data_origin"
    parser = tmp_path / "data_parser"
    indexed = tmp_path / "indexed"
    _create_sample_pdfs(origin)
    monkeypatch.setattr(
        extract_with_docling, "get_optimized_docling_converter", FakeDoclingConverter
    )

    extraction = extract_with_docling.process_data_origin_pipeline(
        origin, parser, is_confirmed=True
    )
    assert extraction["status"] == "success"
    assert extraction["total_files"] == 4
    for category, expected in SAMPLE_MARKDOWN.items():
        markdown_files = list((parser / category).glob("*.md"))
        assert len(markdown_files) == 1
        assert markdown_files[0].read_text(encoding="utf-8") == expected

    indexing_types: list[str] = []

    def indexing_llm(system_prompt: str, user_prompt: str, schema: type):
        doc_type = re.search(r"Loại tài liệu: (\w+)", user_prompt).group(1)
        indexing_types.append(doc_type)
        return _sample_indexing_llm(system_prompt, user_prompt, schema)

    monkeypatch.setattr(run_indexing, "make_llm_call", lambda: indexing_llm)
    monkeypatch.setattr(
        sys, "argv", ["run_indexing.py", str(parser), "--out", str(indexed)]
    )
    run_indexing.main()
    assert set(indexing_types) == set(SAMPLE_MARKDOWN)
    assert len(indexing_types) == 4
    for category in SAMPLE_MARKDOWN:
        outputs = list((indexed / category).glob("*.json"))
        assert len(outputs) == 1
        payload = json.loads(outputs[0].read_text(encoding="utf-8"))
        assert payload["doc_type"] == category
        assert len(payload["chunks"]) == 1
        assert SOURCE_MARKERS[category] in payload["chunks"][0]["text"]

    monkeypatch.setattr("rag.ingest.configured_embedding_provider", lambda: None)
    ingested_count, vector_count, capability = ingest_runtime_corpus(indexed)
    assert ingested_count >= 4
    assert vector_count == 0
    assert "lexical-only" in capability

    vector_store = SQLAlchemyVectorStore()
    rag = RAGQuestionService(
        HybridRetriever(
            dense=DenseRetriever(embedding_provider=None),
            vector_store=vector_store,
        )
    )
    for source_type, marker in SOURCE_MARKERS.items():
        result = rag.retrieve_context(
            POSITION, None, [], question=marker, source_type=source_type
        )
        assert any(
            chunk.chunk.source_type == source_type and marker in chunk.chunk.text
            for chunk in result.chunks
        )
        assert all(chunk.chunk.source_type == source_type for chunk in result.chunks)

    service = interview_routes.service
    llm = SamplePipelineLLM()
    evaluator = SampleAdaptiveEvaluator()
    monkeypatch.setattr(service, "rag", rag)
    monkeypatch.setattr(
        service,
        "agent",
        InterviewAgentCore(
            llm_provider=llm,
            context_retriever=service._retrieve_graph_context,
        ),
    )
    monkeypatch.setattr(service, "evaluator", EvaluationService(evaluator))

    class TestLock:
        def release(self):
            return True

    monkeypatch.setattr(service, "_get_processing_lock", lambda _interview_id: TestLock())
    monkeypatch.setattr(
        interview_routes,
        "report_service",
        ReportService(str(tmp_path / "reports")),
    )

    class TestRedisClient:
        _client = None

        def __init__(self, *_args, **_kwargs):
            pass

        def close(self):
            return None

    monkeypatch.setattr(api_main, "RedisClient", TestRedisClient)

    email = f"task7-{uuid4()}@example.test"
    password = "sample-test-password"
    UserStore.create(email, password, role="admin")
    job_description = next((parser / "jd").glob("*.md")).read_text(encoding="utf-8")
    candidate_resume = next((parser / "cv").glob("*.md")).read_text(encoding="utf-8")

    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        started = client.post(
            "/api/v1/interview/start",
            json={
                "candidate_id": f"task7-candidate-{uuid4()}",
                "position": POSITION,
                "job_description": job_description,
                "candidate_resume": candidate_resume,
                "idempotency_key": f"task7-start-{uuid4()}",
            },
            headers=headers,
        )
        assert started.status_code == 200, started.text
        state = started.json()
        interview_id = state["interview_id"]
        assert len(state["question_plan"]["questions"]) == 10
        assert state["current_question"] == state["question_plan"]["questions"][0][
            "proposal"
        ]["question"]
        assert len(llm.plan_prompts) == 1

        plan_prompt = llm.plan_prompts[0]
        for source_type, marker in SOURCE_MARKERS.items():
            label = f"UNTRUSTED_RETRIEVED_CONTEXT_{source_type.upper()}:\n"
            section = plan_prompt.split(label, 1)[1].split(
                "\n\nUNTRUSTED_RETRIEVED_CONTEXT_", 1
            )[0]
            assert marker in section
            assert all(
                other_marker not in section
                for other_type, other_marker in SOURCE_MARKERS.items()
                if other_type != source_type
            )

        answer_url = f"/api/v1/interview/{interview_id}/answer"
        for index in range(11):
            if index == 0:
                answer = "weak: I changed the Python API but did not measure its result."
            elif index == 1:
                answer = "The change reduced API latency by 20% in production."
            else:
                answer = (
                    f"I owned the work, tested the change, and measured a positive result "
                    f"for planned question {index}."
                )
            request = {"turn_id": f"task7-turn-{index}", "answer": answer}
            response = client.post(answer_url, json=request, headers=headers)
            assert response.status_code == 200, response.text
            state = response.json()
            assert state["history"][-1]["answer"] == answer

            if index == 0:
                assert state["awaiting_follow_up"] is True
                assert state["current_question"] == (
                    "What measurable result did that Python API change produce?"
                )
                replay = client.post(answer_url, json=request, headers=headers)
                assert replay.status_code == 200, replay.text
                assert replay.json()["history"] == state["history"]
                assert len(evaluator.calls) == 1
                assert llm.follow_up_calls == 1
            elif index == 1:
                assert state["awaiting_follow_up"] is False
                assert state["current_question"] == state["question_plan"]["questions"][1][
                    "proposal"
                ]["question"]
            elif index < 10:
                assert state["current_question"] == state["question_plan"]["questions"][
                    index
                ]["proposal"]["question"]

        assert state["status"] == "completed"
        assert len(state["history"]) == 11
        assert state["follow_up_state"]["0"] == "completed"
        assert len(evaluator.calls) == 11
        assert all(call[3].competency == call[2] for call in evaluator.calls)

        report_response = client.post(
            f"/api/v1/interview/{interview_id}/report", headers=headers
        )
        assert report_response.status_code == 200, report_response.text
        report = report_response.json()["report"]
        assert report_response.json()["interview_id"] == interview_id
        assert report["interview_id"] == interview_id
        assert report["is_final"] is True
        assert report["evaluation_status"] == "complete"
        completed_follow_ups = [
            item for item in report["follow_up_results"] if item["status"] == "completed"
        ]
        assert len(report["follow_up_results"]) == 10
        assert len(completed_follow_ups) == 1
        assert completed_follow_ups[0]["follow_up_answer"] == (
            "The change reduced API latency by 20% in production."
        )
        assessments = [
            assessment
            for competency in report["competencies"].values()
            for assessment in competency["question_assessments"]
        ]
        assert len(assessments) == 11
        assert sum(bool(item["rubric"]) for item in assessments) == 11
        assert {
            "weak: I changed the Python API but did not measure its result.",
            "The change reduced API latency by 20% in production.",
        } <= {item["answer_quote"] for item in assessments}

    with SessionLocal() as session:
        persisted = session.get(InterviewRecord, interview_id)
        questions = session.query(InterviewQuestionRecord).filter_by(
            interview_id=interview_id
        ).all()
        turns = session.query(InterviewTurnRecord).filter_by(
            interview_id=interview_id
        ).all()
        assessments = session.query(InterviewAssessmentRecord).filter_by(
            interview_id=interview_id
        ).all()
    assert persisted is not None
    assert len(questions) == 11
    assert len(turns) == 11
    assert len(assessments) == 11
