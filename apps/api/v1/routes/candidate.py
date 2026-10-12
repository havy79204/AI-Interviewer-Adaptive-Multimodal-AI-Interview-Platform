"""Candidate management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from services.auth_service import current_user
from services.candidate_store import CandidateStore

router = APIRouter()
_current_user = Depends(current_user)


class CandidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=4)
    phone: str | None = None
    resume_url: str | None = None


class CandidateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2)
    phone: str | None = None
    resume_url: str | None = None


@router.get("/candidates", tags=["Candidate"])
async def list_candidates(user=_current_user):
    return CandidateStore.list(user["id"], user["role"])


@router.post("/candidates", tags=["Candidate"])
async def create_candidate(payload: CandidatePayload, user=_current_user):
    if user["role"] not in {"admin", "recruiter", "candidate"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    if (
        user["role"] == "candidate"
        and payload.email.strip().lower() != user["sub"].strip().lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate email must match the authenticated account",
        )
    try:
        return CandidateStore.create(payload.model_dump(), user["id"], user["role"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/candidates/{candidate_id}", tags=["Candidate"])
async def get_candidate(candidate_id: str, user=_current_user):
    candidate = CandidateStore.get(candidate_id, user["id"], user["role"])
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.patch("/candidates/{candidate_id}", tags=["Candidate"])
async def update_candidate(candidate_id: str, payload: CandidateUpdate, user=_current_user):
    candidate = CandidateStore.update(
        candidate_id, payload.model_dump(exclude_unset=True), user["id"], user["role"]
    )
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return candidate


@router.delete("/candidates/{candidate_id}", tags=["Candidate"])
async def delete_candidate(candidate_id: str, user=_current_user):
    if not CandidateStore.delete(candidate_id, user["id"], user["role"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return {"deleted": True, "candidate_id": candidate_id}
