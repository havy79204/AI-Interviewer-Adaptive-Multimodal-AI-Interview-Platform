"""Interview API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.interview_agent.graph import QuestionPlanningError

from services.auth_service import current_user
from services.interview_service import (
    InterviewConflictError,
    InterviewEvaluationError,
    InterviewForbiddenError,
    InterviewNotFoundError,
    InterviewProcessingError,
    InterviewStartConflictError,
    InterviewService,
    InterviewUnavailableError,
)
from services.report_service import ReportService

import logging

logger = logging.getLogger(__name__)
router = APIRouter()
_current_user = Depends(current_user)

service = InterviewService()
report_service = ReportService()


class InterviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    mode: str = "text"
    job_description: str | None = Field(default=None, min_length=1)
    candidate_resume: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)

class InterviewAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


@router.post("/interview/start", tags=["Interview"])
async def start_interview(
    payload: InterviewStartRequest, user=_current_user
) -> dict[str, Any]:

    if not payload.job_description or not payload.job_description.strip():
        raise HTTPException(
            status_code=422,
            detail="job_description is required to plan interview questions",
        )
    try:
        return service.start_interview(
            payload.candidate_id,
            payload.position,
            payload.mode,
            user["id"],
            user["role"],
            job_description=payload.job_description,
            candidate_resume=payload.candidate_resume,
            idempotency_key=payload.idempotency_key,
        )
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc
    except InterviewStartConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InterviewProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except QuestionPlanningError as exc:
        logger.error(
            "Interview question planning failed: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Interview question planning is temporarily unavailable",
        ) from exc


@router.post("/interview/{interview_id}/answer", tags=["Interview"])
async def submit_answer(
    interview_id: str, payload: InterviewAnswerRequest, user=_current_user
) -> dict[str, Any]:
    try:
        return service.submit_answer(interview_id, payload.answer, payload.turn_id, user["id"], user["role"])
    except InterviewEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Answer evaluation is temporarily unavailable; retry with the same turn_id.",
        ) from exc
    except InterviewForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InterviewConflictError, InterviewProcessingError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InterviewUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found") from exc


@router.get("/interview/{interview_id}", tags=["Interview"])
async def get_interview(interview_id: str, user=_current_user) -> dict[str, Any]:
    state = service.get_interview(interview_id, user["id"], user["role"])
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return state


@router.get("/interviews", tags=["Interview"])
async def list_interviews(user=_current_user) -> list[dict[str, Any]]:
    return service.list_interviews(user["id"], user["role"])


@router.post("/interview/{interview_id}/report", tags=["Interview"])
async def export_report(
    interview_id: str,
    format: Literal["json", "txt"] = "json",
    user=_current_user,
) -> dict[str, Any]:
    state = service.get_interview(interview_id, user["id"], user["role"])
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    report_path = report_service.export_report(state.get("candidate_id", "unknown"), interview_id, state, format)
    report = report_service.build_report(state.get("candidate_id", "unknown"), interview_id)
    return {
        "interview_id": interview_id,
        "report_file": Path(report_path).name,
        "format": format,
        "report": report,
    }
