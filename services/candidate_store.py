"""Candidate operations scoped to the authenticated resource owner."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from services.database import AccessAuditRecord, CandidateRecord, SessionLocal


class CandidateStore:
    @classmethod
    def create(
        cls,
        payload: dict[str, Any],
        actor_user_id: str | None = None,
        role: str = "admin",
    ) -> dict[str, Any]:
        email = str(payload["email"]).strip().lower()
        owner_user_id = actor_user_id if role in {"recruiter", "admin"} else None
        candidate_user_id = actor_user_id if role == "candidate" else None
        with SessionLocal.begin() as session:
            existing = session.execute(
                select(CandidateRecord).where(CandidateRecord.email == email)
            ).scalar_one_or_none()
            if existing is not None:
                if (
                    role == "admin"
                    or existing.owner_user_id == actor_user_id
                    or existing.user_id == actor_user_id
                ):
                    if role == "admin" and actor_user_id is not None:
                        cls._audit(session, actor_user_id, "read", "candidate", existing.id)
                    return cls._to_dict(existing)
                raise ValueError("Candidate already exists")
            candidate = CandidateRecord(
                name=payload["name"],
                email=email,
                owner_user_id=owner_user_id,
                user_id=candidate_user_id,
                phone=payload.get("phone"),
                resume_url=payload.get("resume_url"),
            )
            session.add(candidate)
            session.flush()
            if role == "admin" and actor_user_id is not None:
                cls._audit(session, actor_user_id, "create", "candidate", candidate.id)
            result = cls._to_dict(candidate)
        return result

    @classmethod
    def list(cls, actor_user_id: str, role: str) -> list[dict[str, Any]]:
        query = select(CandidateRecord).order_by(CandidateRecord.created_at.desc())
        if role == "admin":
            pass
        elif role == "recruiter":
            query = query.where(CandidateRecord.owner_user_id == actor_user_id)
        elif role == "candidate":
            query = query.where(CandidateRecord.user_id == actor_user_id)
        else:
            return []
        with SessionLocal.begin() as session:
            rows = session.execute(query).scalars().all()
            if role == "admin":
                cls._audit(session, actor_user_id, "list", "candidate", "collection")
            return [cls._to_dict(row) for row in rows]

    @classmethod
    def get(cls, candidate_id: str, actor_user_id: str, role: str) -> dict[str, Any] | None:
        with SessionLocal.begin() as session:
            candidate = cls._authorized(session, candidate_id, actor_user_id, role)
            if candidate is None:
                return None
            if role == "admin":
                cls._audit(session, actor_user_id, "read", "candidate", candidate_id)
            return cls._to_dict(candidate)

    @classmethod
    def update(
        cls, candidate_id: str, payload: dict[str, Any], actor_user_id: str, role: str
    ) -> dict[str, Any] | None:
        with SessionLocal.begin() as session:
            candidate = cls._authorized(session, candidate_id, actor_user_id, role)
            if candidate is None:
                return None
            for field in ("name", "phone", "resume_url"):
                if field in payload and (field != "name" or payload[field] is not None):
                    setattr(candidate, field, payload[field])
            candidate.updated_at = datetime.now(UTC)
            if role == "admin":
                cls._audit(session, actor_user_id, "update", "candidate", candidate_id)
            session.flush()
            return cls._to_dict(candidate)

    @classmethod
    def delete(cls, candidate_id: str, actor_user_id: str, role: str) -> bool:
        if role != "admin":
            return False
        with SessionLocal.begin() as session:
            candidate = session.get(CandidateRecord, candidate_id)
            if candidate is None:
                return False
            cls._audit(session, actor_user_id, "delete", "candidate", candidate_id)
            session.delete(candidate)
            return True

    @staticmethod
    def _authorized(session, candidate_id: str, actor_user_id: str, role: str):
        query = select(CandidateRecord).where(CandidateRecord.id == candidate_id)
        if role == "admin":
            pass
        elif role == "recruiter":
            query = query.where(CandidateRecord.owner_user_id == actor_user_id)
        elif role == "candidate":
            query = query.where(CandidateRecord.user_id == actor_user_id)
        else:
            return None
        return session.execute(query).scalar_one_or_none()

    @staticmethod
    def _audit(session, actor_user_id: str, action: str, resource_type: str, resource_id: str) -> None:
        session.add(
            AccessAuditRecord(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    @staticmethod
    def _to_dict(candidate: CandidateRecord) -> dict[str, Any]:
        return {
            "id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "resume_url": candidate.resume_url,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
        }
