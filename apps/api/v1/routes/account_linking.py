"""Recruiter invitation and audited out-of-band email verification routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from services.auth_service import current_user
from services.candidate_invitation_service import (
    CandidateInvitationService,
    InvitationOperationError,
)

router = APIRouter()
_current_user = Depends(current_user)


class InvitationRedemptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=1, max_length=128)


class EmailVerificationAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: Literal["confirmed_out_of_band"]


def _raise_operation_error(error: InvitationOperationError) -> None:
    raise HTTPException(
        status_code=error.status_code, detail=error.message
    ) from error


@router.post(
    "/candidates/{candidate_id}/invitations",
    status_code=status.HTTP_201_CREATED,
    tags=["Candidate invitations"],
    summary="Create a single-use invitation for an owned candidate profile",
)
async def create_candidate_invitation(candidate_id: str, user=_current_user):
    """Return the token once; deliver it to the already verified candidate out of band."""
    try:
        invitation = CandidateInvitationService.create(
            candidate_id, user["id"], user["role"]
        )
    except InvitationOperationError as exc:
        _raise_operation_error(exc)
    return invitation


@router.delete(
    "/candidates/{candidate_id}/invitations",
    tags=["Candidate invitations"],
    summary="Revoke the pending invitation for an owned candidate profile",
)
async def revoke_candidate_invitation(candidate_id: str, user=_current_user):
    try:
        CandidateInvitationService.revoke(
            candidate_id, user["id"], user["role"]
        )
    except InvitationOperationError as exc:
        _raise_operation_error(exc)
    return {"revoked": True}


@router.post(
    "/candidate-invitations/redeem",
    tags=["Candidate invitations"],
    summary="Redeem an invitation as its verified candidate account",
)
async def redeem_candidate_invitation(
    payload: InvitationRedemptionRequest, user=_current_user
):
    try:
        return CandidateInvitationService.redeem(payload.token, user["id"])
    except InvitationOperationError as exc:
        _raise_operation_error(exc)


@router.post(
    "/admin/users/{user_id}/verify-email",
    tags=["Administration"],
    summary="Record an administrator's out-of-band email verification",
)
async def verify_user_email(
    user_id: str,
    payload: EmailVerificationAttestation,
    user=_current_user,
):
    try:
        return CandidateInvitationService.verify_email_out_of_band(
            user_id, user["id"], user["role"]
        )
    except InvitationOperationError as exc:
        _raise_operation_error(exc)
