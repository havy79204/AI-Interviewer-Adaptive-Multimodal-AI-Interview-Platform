"""Application service for interview lifecycle operations."""

from __future__ import annotations

import json
import secrets
from hashlib import sha256
from datetime import UTC, datetime
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from agents.interview_agent.graph import (
    InterviewAgentCore,
    InterviewQuestionPlan,
    QuestionPlanningError,
)
from config import settings
from evaluation.service import (
    DeterministicEvaluator,
    EvaluationContext,
    EvaluationService,
    LLMEvaluator,
    Rubric,
)
from infrastructure.distributed_lock import (
    DistributedLock,
    LockAcquisitionTimeout,
    RedisUnavailableError,
)
from infrastructure.redis_store import RedisClient, RedisStore
from integrations.llm_providers.provider import (
    LLMConfigurationError,
    LLMProviderError,
    provider_from_settings,
)
from rag.service import RAGQuestionService
from services.database import AccessAuditRecord, InterviewRecord, SessionLocal
from services.repositories import (
    EvaluationRepository,
    InterviewRepository,
    QuestionRepository,
    TurnRepository,
)
from services.turn_state import TurnStatus


class InterviewNotFoundError(LookupError):
    """Raised when an interview does not exist."""


class InterviewForbiddenError(PermissionError):
    """Raised when a user is authenticated but cannot perform an operation."""


class InterviewConflictError(RuntimeError):
    """Raised when a turn ID is reused with a different answer payload."""


class InterviewStartConflictError(RuntimeError):
    """Raised when an interview-start idempotency key is reused for another request."""


class InterviewProcessingError(RuntimeError):
    """Raised when another request is still processing this interview."""


class InterviewUnavailableError(RuntimeError):
    """Raised when safe distributed processing cannot be guaranteed."""


class InterviewEvaluationError(RuntimeError):
    """Raised when an answer cannot be evaluated and should be retried."""


class InterviewService:
    """Coordinates interview decisions and persistence within explicit transactions."""

    def __init__(
        self,
        agent: InterviewAgentCore | None = None,
        evaluator: EvaluationService | None = None,
        rag: RAGQuestionService | None = None,
        interview_repository: InterviewRepository | None = None,
        turn_repository: TurnRepository | None = None,
        evaluation_repository: EvaluationRepository | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self.rag = rag or RAGQuestionService()
        self._llm_configuration_error: LLMConfigurationError | None = None
        try:
            llm_provider = provider_from_settings(settings)
        except LLMConfigurationError as exc:
            llm_provider = None
            if agent is None:
                self._llm_configuration_error = exc
        self.agent = agent or InterviewAgentCore(
            llm_provider=llm_provider,
            context_retriever=self._retrieve_graph_context,
        )
        if evaluator is not None:
            self.evaluator = evaluator
        elif llm_provider is not None:
            self.evaluator = EvaluationService(LLMEvaluator(llm_provider))
        else:
            self.evaluator = EvaluationService(DeterministicEvaluator())
        self.interviews = interview_repository or InterviewRepository()
        self.turns = turn_repository or TurnRepository()
        self.evaluations = evaluation_repository or EvaluationRepository()
        self.questions = QuestionRepository()
        self.redis_client = redis_client or (RedisClient(settings.REDIS_URL, namespace="interview") if settings.REDIS_URL else None)
        self.redis_store = RedisStore(self.redis_client, namespace="interview") if self.redis_client is not None else None

    def _plan_questions(
        self,
        position: str,
        job_description: str,
        candidate_resume: str | None = None,
    ) -> InterviewQuestionPlan:
        """Plan questions from the JD; use the resume only when it is available."""
        configuration_error = getattr(self, "_llm_configuration_error", None)
        if configuration_error is not None:
            raise QuestionPlanningError(
                f"LLM provider configuration is unavailable: {configuration_error}"
            ) from configuration_error
        if not job_description or not job_description.strip():
            raise QuestionPlanningError(
                "question planning requires a non-empty job description"
            )
        return self.agent.plan_questions(
            position,
            job_description,
            candidate_resume or "",
        )

    def _get_processing_lock(self, interview_id: str) -> DistributedLock | None:
        if self.redis_client is None:
            return None
        lock_name = self.redis_store._key(f"processing:{interview_id}") if self.redis_store is not None else f"interview:processing:{interview_id}"
        lock = DistributedLock(
            self.redis_client,
            lock_name,
            ttl_seconds=settings.REDIS_LOCK_TTL_SECONDS,
            acquire_timeout_seconds=settings.REDIS_LOCK_ACQUIRE_TIMEOUT_SECONDS,
        )
        if not lock.acquire():
            return None
        return lock

    def _release_processing_lock(self, interview_id: str, lock: DistributedLock | None) -> None:
        if lock is None:
            return
        lock.release()

    def start_interview(
        self,
        candidate_id: str,
        position: str,
        mode: str = "text",
        owner_user_id: str | None = None,
        owner_role: str = "candidate",
        job_description: str | None = None,
        candidate_resume: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if job_description is None or not job_description.strip():
            raise QuestionPlanningError(
                "question planning requires a non-empty job description"
            )
        start_request_hash = None
        if idempotency_key is not None:
            start_request_hash = self._start_request_hash(
                candidate_id,
                position,
                mode,
                owner_user_id,
                owner_role,
                job_description,
                candidate_resume,
            )
            return self._start_idempotent(
                candidate_id=candidate_id,
                position=position,
                mode=mode,
                owner_user_id=owner_user_id,
                owner_role=owner_role,
                job_description=job_description,
                candidate_resume=candidate_resume,
                request_key=idempotency_key,
                request_hash=start_request_hash,
            )
        with SessionLocal() as session:
            if not self.interviews.can_manage_candidate(
                session, candidate_id, owner_user_id or "", owner_role
            ):
                raise InterviewNotFoundError(candidate_id)

        question_plan = self._plan_questions(
            position,
            job_description,
            candidate_resume,
        )
        state = self.agent.start_interview(
            candidate_id=candidate_id,
            position=position,
            question_plan=question_plan,
        )
        interview_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        state.update(
            {
                "interview_id": interview_id,
                "mode": mode,
                "created_at": now,
                "updated_at": now,
            }
        )
        with SessionLocal.begin() as session:
            if not self.interviews.can_manage_candidate(
                session, candidate_id, owner_user_id or "", owner_role
            ):
                raise InterviewNotFoundError(candidate_id)
            self.interviews.create(
                session,
                state,
                owner_user_id,
            )
            if owner_role == "admin" and owner_user_id is not None:
                self._audit_admin(session, owner_user_id, "create", interview_id)
        return state

    def _start_idempotent(
        self,
        *,
        candidate_id: str,
        position: str,
        mode: str,
        owner_user_id: str | None,
        owner_role: str,
        job_description: str | None,
        candidate_resume: str | None,
        request_key: str,
        request_hash: str,
    ) -> dict[str, Any]:
        request_owner = secrets.token_urlsafe(24)
        wait_seconds = max(60.0, settings.LLM_TIMEOUT_SECONDS * 3.0)
        deadline = monotonic() + wait_seconds

        while True:
            with SessionLocal() as session:
                if not self.interviews.can_manage_candidate(
                    session, candidate_id, owner_user_id or "", owner_role
                ):
                    raise InterviewNotFoundError(candidate_id)
                existing = session.scalar(
                    select(InterviewRecord).where(
                        InterviewRecord.start_request_key == request_key
                    )
                )
                if existing is not None:
                    if existing.start_request_hash != request_hash:
                        raise InterviewStartConflictError(
                            "idempotency_key was already used for a different start request"
                        )
                    if existing.start_request_status != "planning":
                        return self._state(existing)

            if existing is not None:
                if monotonic() >= deadline:
                    raise InterviewProcessingError(
                        "Interview start is still being processed; retry with the same idempotency_key."
                    )
                sleep(0.025)
                continue

            interview_id = str(uuid4())
            now = datetime.now(UTC)
            try:
                with SessionLocal.begin() as session:
                    if not self.interviews.can_manage_candidate(
                        session, candidate_id, owner_user_id or "", owner_role
                    ):
                        raise InterviewNotFoundError(candidate_id)
                    self.interviews.reserve_start(
                        session,
                        interview_id=interview_id,
                        candidate_id=candidate_id,
                        position=position,
                        mode=mode,
                        owner_user_id=owner_user_id,
                        request_key=request_key,
                        request_hash=request_hash,
                        request_owner=request_owner,
                        now=now,
                    )
            except IntegrityError:
                with SessionLocal() as session:
                    claimed_request = session.scalar(
                        select(InterviewRecord).where(
                            InterviewRecord.start_request_key == request_key
                        )
                    )
                if claimed_request is None:
                    raise
                continue
            break

        reservation_completed = False
        try:
            question_plan = self._plan_questions(
                position,
                job_description or "",
                candidate_resume,
            )
            state = self.agent.start_interview(
                candidate_id=candidate_id,
                position=position,
                question_plan=question_plan,
            )
            now_iso = datetime.now(UTC).isoformat()
            state.update(
                {
                    "interview_id": interview_id,
                    "mode": mode,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
            )
            with SessionLocal.begin() as session:
                completed = self.interviews.complete_start(
                    session,
                    interview_id=interview_id,
                    request_owner=request_owner,
                    state=state,
                )
                if completed and owner_role == "admin" and owner_user_id is not None:
                    self._audit_admin(session, owner_user_id, "create", interview_id)
            reservation_completed = completed
            if not completed:
                raise InterviewProcessingError(
                    "Interview start reservation was lost; retry with the same idempotency_key."
                )
            return state
        finally:
            if not reservation_completed:
                with SessionLocal.begin() as session:
                    self.interviews.release_start_reservation(
                        session, interview_id, request_owner
                    )

    @staticmethod
    def _start_request_hash(
        candidate_id: str,
        position: str,
        mode: str,
        owner_user_id: str | None,
        owner_role: str,
        job_description: str | None,
        candidate_resume: str | None,
    ) -> str:
        canonical_request = json.dumps(
            {
                "candidate_id": candidate_id,
                "position": position,
                "mode": mode,
                "owner_user_id": owner_user_id,
                "owner_role": owner_role,
                "job_description": job_description,
                "candidate_resume": candidate_resume,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical_request.encode("utf-8")).hexdigest()

    def get_interview(self, interview_id: str, user_id: str | None = None, role: str = "candidate") -> dict[str, Any] | None:
        with SessionLocal.begin() as session:
            interview = self.interviews.get_authorized(session, interview_id, user_id or "", role)
            if interview is None:
                return None
            if role == "admin" and user_id is not None:
                self._audit_admin(session, user_id, "read", interview_id)
            return self._state(interview)

    def list_interviews(self, user_id: str | None = None, role: str = "candidate") -> list[dict[str, Any]]:
        with SessionLocal.begin() as session:
            interviews = self.interviews.list_authorized(session, user_id or "", role)
            if role == "admin" and user_id is not None:
                self._audit_admin(session, user_id, "list", "collection")
            return [self._state(interview) for interview in interviews]

    def submit_answer(
        self, interview_id: str, answer: str, turn_id: str, user_id: str | None = None, role: str = "candidate"
    ) -> dict[str, Any]:
        if role == "recruiter":
            raise InterviewForbiddenError("Recruiters have read-only interview access")
        lock = self._acquire_submission_lock(interview_id, answer, turn_id, user_id, role)
        try:
            replay = self._prepare_turn(interview_id, answer, turn_id, user_id, role)
            if replay is not None:
                return replay
            return self._process_turn(interview_id, answer, turn_id, user_id, role)
        finally:
            self._release_processing_lock(interview_id, lock)

    def _acquire_submission_lock(
        self,
        interview_id: str,
        answer: str,
        turn_id: str,
        user_id: str | None,
        role: str,
    ) -> DistributedLock:
        with SessionLocal() as session:
            if self.interviews.get_authorized(session, interview_id, user_id or "", role) is None:
                raise InterviewNotFoundError(interview_id)
        try:
            lock = self._get_processing_lock(interview_id)
        except LockAcquisitionTimeout as exc:
            with SessionLocal() as session:
                existing_turn = self.turns.get_by_client_id(session, interview_id, turn_id)
                if existing_turn is not None and existing_turn.candidate_answer != answer:
                    raise InterviewConflictError(
                        "turn_id was already used with a different answer"
                    ) from exc
            raise InterviewProcessingError(
                "Interview is still processing; retry the same turn_id and answer."
            ) from exc
        except RedisUnavailableError as exc:
            raise InterviewUnavailableError(
                "Cannot safely process interview while distributed locking is unavailable"
            ) from exc
        if lock is None:
            raise InterviewUnavailableError(
                "Cannot safely process interview without distributed locking"
            )
        return lock

    def _prepare_turn(
        self,
        interview_id: str,
        answer: str,
        turn_id: str,
        user_id: str | None,
        role: str,
    ) -> dict[str, Any] | None:
        try:
            with SessionLocal.begin() as session:
                interview = self.interviews.get_authorized(session, interview_id, user_id or "", role)
                if interview is None:
                    raise InterviewNotFoundError(interview_id)
                if role == "admin" and user_id is not None:
                    self._audit_admin(session, user_id, "answer", interview_id)
                existing_turn = self.turns.get_by_client_id(session, interview_id, turn_id)
                if existing_turn is not None:
                    if not self._claim_existing_turn(existing_turn, answer):
                        return self._state(interview)
                else:
                    state = self._state(interview)
                    if state.get("status") == "completed":
                        raise InterviewConflictError("Interview has already been completed")
                    self.turns.create_processing(session, interview_id, turn_id, answer)
        except IntegrityError as exc:
            with SessionLocal() as session:
                interview = self.interviews.get_authorized(session, interview_id, user_id or "", role)
                if interview is None:
                    raise InterviewNotFoundError(interview_id) from exc
                existing_turn = self.turns.get_by_client_id(session, interview_id, turn_id)
                if existing_turn is not None and existing_turn.candidate_answer != answer:
                    raise InterviewConflictError(
                        "turn_id was already used with a different answer"
                    ) from exc
                return self._state(interview)
        return None

    def _claim_existing_turn(self, turn: Any, answer: str) -> bool:
        if turn.candidate_answer != answer:
            raise InterviewConflictError("turn_id was already used with a different answer")
        if turn.status == TurnStatus.FAILED_RETRYABLE:
            self.turns.transition(turn, TurnStatus.PROCESSING)
            return True
        if self.turns.reclaim_if_stale(turn, settings.TURN_PROCESSING_LEASE_SECONDS):
            return True
        if turn.status == TurnStatus.PROCESSING:
            raise InterviewProcessingError(
                "Interview is still processing; retry the same turn_id and answer."
            )
        if turn.status == TurnStatus.COMPLETED:
            return False
        if turn.status == TurnStatus.RECEIVED:
            raise InterviewProcessingError(
                "Interview is still processing; retry the same turn_id and answer."
            )
        raise InterviewConflictError("turn has failed permanently and cannot be replayed")

    def _process_turn(
        self,
        interview_id: str,
        answer: str,
        turn_id: str,
        user_id: str | None,
        role: str,
    ) -> dict[str, Any]:
        try:
            with SessionLocal.begin() as session:
                interview = self.interviews.get_authorized(session, interview_id, user_id or "", role)
                if interview is None:
                    raise InterviewNotFoundError(interview_id)
                persisted_turn = self.turns.get_by_client_id(session, interview_id, turn_id)
                if persisted_turn is None:
                    raise InterviewNotFoundError(interview_id)
                state = self._state(interview)
                if self.evaluations.has_assessment(session, interview_id, persisted_turn.id):
                    if persisted_turn.status == TurnStatus.PROCESSING:
                        self.turns.transition(persisted_turn, TurnStatus.COMPLETED)
                    return state
                asked_questions = self.questions.list_for_interview(session, interview_id)
                asked_question = asked_questions[-1] if asked_questions else None
                planned_questions = state.get("question_plan", {}).get("questions", [])
                planned_index = int(
                    state.get("planned_question_index", len(state.get("history", [])))
                )
                planned_question = (
                    planned_questions[planned_index]
                    if planned_index < len(planned_questions)
                    else None
                )
                question_text = (
                    asked_question.question_text
                    if asked_question is not None
                    else state.get("current_question", "")
                )
                target_competency = (
                    planned_question["proposal"]["competency"]
                    if planned_question is not None
                    else (
                        (asked_question.competency if asked_question is not None else None)
                        or state.get("current_competency")
                        or "general"
                    )
                )
                rubric = (
                    Rubric.model_validate(planned_question["rubric"])
                    if planned_question is not None
                    else Rubric(competency=target_competency)
                )
                evaluation_context = EvaluationContext(
                    position=str(state.get("position", "")),
                    prior_answers=[
                        str(item.get("answer", ""))
                        for item in state.get("history", [])[-5:]
                        if item.get("answer")
                    ],
                    competency_state=state.get("skills", {}),
                    identified_gaps=state.get("identified_gaps", []),
                )
                try:
                    result = self.evaluator.evaluate_result(
                        question_text,
                        answer,
                        target_competency,
                        rubric,
                        evaluation_context,
                    )
                except LLMProviderError as exc:
                    raise InterviewEvaluationError(
                        "Answer evaluation is unavailable; retry this turn."
                    ) from exc
                persisted_turn.question_id = asked_question.id if asked_question is not None else None
                graph_state = dict(state)
                graph_state["questions_asked"] = [item.question_text for item in asked_questions]
                updated_state = self.agent.handle_answer(
                    graph_state,
                    answer,
                    turn_id,
                    evaluation=result,
                    rubric=rubric,
                    asked_questions=graph_state["questions_asked"],
                )
                updated_state["follow_up_questions"] = self.rag.retrieve_relevant_questions(
                    updated_state.get("position", ""), updated_state.get("skills", {})
                )
                evaluation = self.evaluator.summarize(
                    result,
                    updated_state.get("position", ""),
                    updated_state.get("skills", {}),
                )
                question_id = asked_question.id if asked_question is not None else None
                self.evaluations.save_result(session, interview_id, persisted_turn, question_id, result)
                updated_state["evaluation"] = evaluation
                updated_state["overall_score"] = evaluation["overall_score"]
                updated_state["recommended_next_action"] = updated_state["next_action"]
                history_entry = updated_state["history"][-1]
                history_entry.update(
                    {
                        "question": question_text,
                        "rubric": rubric.model_dump(mode="json"),
                        "assessment": result.assessment.model_dump(mode="json"),
                        "is_follow_up": bool(state.get("awaiting_follow_up", False)),
                        "planned_question_index": int(
                            state.get("planned_question_index", 0)
                        ),
                    }
                )
                updated_state["updated_at"] = datetime.now(UTC).isoformat()
                self.interviews.save_state(session, interview, updated_state, persisted_turn)
                return updated_state
        except Exception:
            with SessionLocal.begin() as session:
                failed_turn = self.turns.get_by_client_id(session, interview_id, turn_id)
                if failed_turn is not None and failed_turn.status == TurnStatus.PROCESSING:
                    self.turns.transition(failed_turn, TurnStatus.FAILED_RETRYABLE)
            raise

    def _retrieve_graph_context(self, state: dict[str, Any]) -> str:
        result = self.rag.retrieve_context(
            str(state.get("position", "")),
            state.get("current_competency"),
            state.get("identified_gaps", []),
            question=state.get("planning_query") or state.get("current_question"),
            answer_evidence=[str(state.get("candidate_answer", ""))],
            previous_questions=state.get("asked_questions", []),
            difficulty=state.get("difficulty"),
            source_type=state.get("planning_source_type"),
            job_id=state.get("job_id") or state.get("interview_template_id"),
            organization_id=state.get("organization_id"),
        )
        if result.fallback_reason and result.fallback_reason.startswith("retrieval_failed:"):
            raise RuntimeError("Interview question context retrieval failed")
        return self.rag.format_context(result)

    @staticmethod
    def _state(interview: Any) -> dict[str, Any]:
        state = json.loads(interview.state_json)
        state.update({
            "interview_id": interview.id,
            "candidate_id": interview.candidate_id,
            "position": interview.position,
            "mode": interview.mode,
            "current_question": interview.current_question,
        })
        return state

    @staticmethod
    def _audit_admin(session, user_id: str, action: str, resource_id: str) -> None:
        session.add(AccessAuditRecord(
            actor_user_id=user_id,
            action=action,
            resource_type="interview",
            resource_id=resource_id,
        ))
