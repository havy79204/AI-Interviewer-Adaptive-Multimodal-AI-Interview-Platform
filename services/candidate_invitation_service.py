"""Audited recruiter invitations for linking verified candidate accounts."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from services.database import (
    AccessAuditRecord,
    CandidateInvitationRecord,
    CandidateRecord,
    SessionLocal,
    UserRecord,
)

INVITATION_TTL = timedelta(hours=72)
INVITATION_COOLDOWN = timedelta(minutes=1)
INVITATION_ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_RECRUITER_INVITATIONS_PER_HOUR = 20
MAX_REDEMPTION_ATTEMPTS_PER_WINDOW = 20
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,128}$")
UNAVAILABLE_MESSAGE = "Invitation is invalid or unavailable"


class InvitationOperationError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class _InvalidLink(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class CandidateInvitationService:
    @staticmethod
    def _attempt_link(
        session, token: str, candidate_user_id: str, now: datetime
    ) -> str | None:
        user = session.get(UserRecord, candidate_user_id)
        if (
            not TOKEN_PATTERN.fullmatch(token)
            or user is None
            or user.role != "candidate"
            or user.email_verified_at is None
        ):
            return None

        token_hash = _token_digest(token)
        invitation = session.execute(
            select(CandidateInvitationRecord)
            .where(CandidateInvitationRecord.token_hash == token_hash)
        ).scalar_one_or_none()
        if invitation is None:
            return None

        candidate = session.execute(
            select(CandidateRecord)
            .where(CandidateRecord.id == invitation.candidate_id)
            .with_for_update()
        ).scalar_one_or_none()
        if candidate is None:
            return None
        invitation = session.execute(
            select(CandidateInvitationRecord)
            .where(
                CandidateInvitationRecord.id == invitation.id,
                CandidateInvitationRecord.token_hash == token_hash,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if invitation is None:
            return None
        if (
            invitation.consumed_at is not None
            or invitation.revoked_at is not None
            or _aware_utc(invitation.expires_at) <= now
            or normalize_email(invitation.email) != normalize_email(user.email)
            or candidate.user_id is not None
            or candidate.owner_user_id != invitation.recruiter_user_id
            or normalize_email(candidate.email) != invitation.email
        ):
            return None

        try:
            with session.begin_nested():
                linked = session.execute(
                    update(CandidateRecord)
                    .where(
                        CandidateRecord.id == invitation.candidate_id,
                        CandidateRecord.owner_user_id == invitation.recruiter_user_id,
                        CandidateRecord.user_id.is_(None),
                        CandidateRecord.email == invitation.email,
                    )
                    .values(user_id=candidate_user_id)
                )
                if linked.rowcount != 1:
                    raise _InvalidLink
                consumed = session.execute(
                    update(CandidateInvitationRecord)
                    .where(
                        CandidateInvitationRecord.id == invitation.id,
                        CandidateInvitationRecord.consumed_at.is_(None),
                        CandidateInvitationRecord.revoked_at.is_(None),
                        CandidateInvitationRecord.expires_at > now,
                    )
                    .values(consumed_at=now)
                    .execution_options(synchronize_session=False)
                )
                if consumed.rowcount != 1:
                    raise _InvalidLink
                session.add(
                    AccessAuditRecord(
                        actor_user_id=candidate_user_id,
                        action="link",
                        resource_type="candidate",
                        resource_id=invitation.candidate_id,
                    )
                )
                return invitation.candidate_id
        except (_InvalidLink, IntegrityError):
            return None

    @classmethod
    def create(
        cls, candidate_id: str, recruiter_user_id: str, role: str
    ) -> dict[str, Any]:
        if role != "recruiter":
            raise InvitationOperationError(403, "Recruiter role required")

        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        try:
            with SessionLocal.begin() as session:
                recruiter = session.execute(
                    select(UserRecord.id)
                    .where(UserRecord.id == recruiter_user_id)
                    .with_for_update()
                ).scalar_one_or_none()
                if recruiter is None:
                    raise InvitationOperationError(403, "Recruiter role required")
                candidate = session.execute(
                    select(CandidateRecord).where(
                        CandidateRecord.id == candidate_id,
                        CandidateRecord.owner_user_id == recruiter_user_id,
                    ).with_for_update()
                ).scalar_one_or_none()
                if candidate is None:
                    raise InvitationOperationError(404, "Candidate not found")
                if candidate.user_id is not None:
                    raise InvitationOperationError(
                        409, "Candidate profile is not eligible for an invitation"
                    )

                verified_user = session.execute(
                    select(UserRecord).where(
                        UserRecord.email == normalize_email(candidate.email),
                        UserRecord.email_verified_at.is_not(None),
                        UserRecord.role == "candidate",
                    )
                ).scalar_one_or_none()
                if verified_user is None:
                    raise InvitationOperationError(
                        409, "Candidate profile is not eligible for an invitation"
                    )

                last_candidate_invitation = session.execute(
                    select(CandidateInvitationRecord.created_at)
                    .where(CandidateInvitationRecord.candidate_id == candidate_id)
                    .order_by(CandidateInvitationRecord.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if (
                    last_candidate_invitation is not None
                    and _aware_utc(last_candidate_invitation)
                    > now - INVITATION_COOLDOWN
                ):
                    raise InvitationOperationError(
                        429, "Invitation creation is temporarily limited"
                    )

                recruiter_invitation_count = session.execute(
                    select(func.count(CandidateInvitationRecord.id)).where(
                        CandidateInvitationRecord.recruiter_user_id
                        == recruiter_user_id,
                        CandidateInvitationRecord.created_at
                        >= now - timedelta(hours=1),
                    )
                ).scalar_one()
                if recruiter_invitation_count >= MAX_RECRUITER_INVITATIONS_PER_HOUR:
                    raise InvitationOperationError(
                        429, "Invitation creation is temporarily limited"
                    )

                session.execute(
                    update(CandidateInvitationRecord)
                    .where(
                        CandidateInvitationRecord.candidate_id == candidate_id,
                        CandidateInvitationRecord.consumed_at.is_(None),
                        CandidateInvitationRecord.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
                invitation = CandidateInvitationRecord(
                    candidate_id=candidate_id,
                    recruiter_user_id=recruiter_user_id,
                    email=normalize_email(candidate.email),
                    token_hash=_token_digest(token),
                    expires_at=now + INVITATION_TTL,
                )
                session.add(invitation)
                session.flush()
                session.add(
                    AccessAuditRecord(
                        actor_user_id=recruiter_user_id,
                        action="create",
                        resource_type="candidate_invitation",
                        resource_id=invitation.id,
                    )
                )
                return {
                    "invitation_id": invitation.id,
                    "token": token,
                    "expires_at": invitation.expires_at,
                }
        except IntegrityError as exc:
            raise InvitationOperationError(
                429, "Invitation creation is temporarily limited"
            ) from exc

    @classmethod
    def revoke(cls, candidate_id: str, recruiter_user_id: str, role: str) -> None:
        if role != "recruiter":
            raise InvitationOperationError(403, "Recruiter role required")

        now = datetime.now(UTC)
        with SessionLocal.begin() as session:
            candidate = session.execute(
                select(CandidateRecord.id).where(
                    CandidateRecord.id == candidate_id,
                    CandidateRecord.owner_user_id == recruiter_user_id,
                ).with_for_update()
            ).scalar_one_or_none()
            if candidate is None:
                raise InvitationOperationError(404, "Candidate not found")
            invitation_id = session.execute(
                update(CandidateInvitationRecord)
                .where(
                    CandidateInvitationRecord.candidate_id == candidate_id,
                    CandidateInvitationRecord.recruiter_user_id == recruiter_user_id,
                    CandidateInvitationRecord.consumed_at.is_(None),
                    CandidateInvitationRecord.revoked_at.is_(None),
                )
                .values(revoked_at=now)
                .returning(CandidateInvitationRecord.id)
            ).scalar_one_or_none()
            if invitation_id is None:
                raise InvitationOperationError(
                    404, "Candidate invitation not found"
                )
            session.add(
                AccessAuditRecord(
                    actor_user_id=recruiter_user_id,
                    action="revoke",
                    resource_type="candidate_invitation",
                    resource_id=invitation_id,
                )
            )

    @classmethod
    def redeem(cls, token: str, candidate_user_id: str) -> dict[str, str]:
        now = datetime.now(UTC)
        invalid = False
        rate_limited = False
        linked_candidate_id: str | None = None
        try:
            with SessionLocal.begin() as session:
                locked_user_id = session.execute(
                    select(UserRecord.id)
                    .where(UserRecord.id == candidate_user_id)
                    .with_for_update()
                ).scalar_one_or_none()
                if locked_user_id is None:
                    invalid = True
                else:
                    recent_attempts = session.execute(
                        select(func.count(AccessAuditRecord.id)).where(
                            AccessAuditRecord.actor_user_id == candidate_user_id,
                            AccessAuditRecord.action
                            == "candidate_invitation_redemption_attempt",
                            AccessAuditRecord.created_at
                            >= now - INVITATION_ATTEMPT_WINDOW,
                        )
                    ).scalar_one()
                    if recent_attempts >= MAX_REDEMPTION_ATTEMPTS_PER_WINDOW:
                        rate_limited = True
                    else:
                        session.add(
                            AccessAuditRecord(
                                actor_user_id=candidate_user_id,
                                action="candidate_invitation_redemption_attempt",
                                resource_type="user",
                                resource_id=candidate_user_id,
                            )
                        )
                        linked_candidate_id = cls._attempt_link(
                            session, token, candidate_user_id, now
                        )
                        invalid = linked_candidate_id is None
        except IntegrityError as exc:
            raise InvitationOperationError(400, UNAVAILABLE_MESSAGE) from exc

        if rate_limited:
            raise InvitationOperationError(429, "Redemption is temporarily limited")
        if invalid or linked_candidate_id is None:
            raise InvitationOperationError(400, UNAVAILABLE_MESSAGE)
        return {"candidate_id": linked_candidate_id}

    @classmethod
    def verify_email_out_of_band(
        cls, user_id: str, admin_user_id: str, role: str
    ) -> dict[str, Any]:
        if role != "admin":
            raise InvitationOperationError(403, "Admin role required")
        now = datetime.now(UTC)
        with SessionLocal.begin() as session:
            target = session.get(UserRecord, user_id)
            if target is None:
                raise InvitationOperationError(404, "User not found")
            if target.email_verified_at is not None:
                raise InvitationOperationError(409, "Email is already verified")
            target.email_verified_at = now
            session.add(
                AccessAuditRecord(
                    actor_user_id=admin_user_id,
                    action="verify_email_out_of_band",
                    resource_type="user",
                    resource_id=user_id,
                )
            )
            return {"user_id": user_id, "email_verified_at": now}
