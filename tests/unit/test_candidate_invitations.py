from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from apps.api.main import app
from services.auth_service import issue_token
from services.database import (
    AccessAuditRecord,
    CandidateInvitationRecord,
    CandidateRecord,
    SessionLocal,
    UserRecord,
)
from services.user_store import UserStore


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user(role: str, email: str | None = None) -> tuple[dict, dict[str, str]]:
    email = email or f"{role}-{uuid4()}@example.com"
    user = UserStore.create(email, "secret123", role=role)
    token = issue_token(email, role)
    return user, {"Authorization": f"Bearer {token}"}


def create_candidate(client: TestClient, headers: dict[str, str], email: str) -> dict:
    response = client.post(
        "/api/v1/candidates",
        json={"name": "Invitation Candidate", "email": email},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def verify_email(client: TestClient, admin_headers: dict[str, str], user_id: str):
    return client.post(
        f"/api/v1/admin/users/{user_id}/verify-email",
        json={"confirmation": "confirmed_out_of_band"},
        headers=admin_headers,
    )


def create_invitation(
    client: TestClient, recruiter_headers: dict[str, str], candidate_id: str
):
    return client.post(
        f"/api/v1/candidates/{candidate_id}/invitations",
        headers=recruiter_headers,
    )


def test_verified_candidate_links_profile_and_keeps_authorization(
    client: TestClient,
):
    recruiter, recruiter_headers = create_user("recruiter")
    candidate_user, candidate_headers = create_user("candidate")
    other_recruiter, other_recruiter_headers = create_user("recruiter")
    admin, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, candidate_user["email"])
    outsider_profile = create_candidate(
        client, other_recruiter_headers, f"outsider-{uuid4()}@example.com"
    )
    outsider_interview = client.post(
        "/api/v1/interview/start",
        json={
            "candidate_id": outsider_profile["id"],
            "position": "Synthetic Engineer",
        },
        headers=other_recruiter_headers,
    )
    assert outsider_interview.status_code == 200, outsider_interview.text

    assert verify_email(client, admin_headers, candidate_user["id"]).status_code == 200
    assert create_invitation(
        client, other_recruiter_headers, profile["id"]
    ).status_code == 404
    invitation_response = create_invitation(
        client, recruiter_headers, profile["id"]
    )
    assert invitation_response.status_code == 201, invitation_response.text
    invitation = invitation_response.json()
    token = invitation["token"]

    with SessionLocal() as session:
        stored = session.get(CandidateInvitationRecord, invitation["invitation_id"])
        assert stored is not None
        assert stored.token_hash == sha256(token.encode()).hexdigest()
        assert token != stored.token_hash
        assert stored.email == candidate_user["email"].lower()
        assert recruiter["id"] == stored.recruiter_user_id

    interview = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": profile["id"], "position": "Synthetic Engineer"},
        headers=recruiter_headers,
    )
    assert interview.status_code == 200, interview.text
    interview_id = interview.json()["interview_id"]

    redemption = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": token},
        headers=candidate_headers,
    )
    assert redemption.status_code == 200, redemption.text
    assert redemption.json() == {"candidate_id": profile["id"]}

    assert client.get(
        f"/api/v1/candidates/{profile['id']}", headers=candidate_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/interview/{interview_id}", headers=candidate_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/candidates/{outsider_profile['id']}", headers=candidate_headers
    ).status_code == 404
    assert client.get(
        f"/api/v1/interview/{outsider_interview.json()['interview_id']}",
        headers=candidate_headers,
    ).status_code == 404

    answer = {"turn_id": f"linked-{uuid4()}", "answer": "I delivered a Python API."}
    first = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json=answer,
        headers=candidate_headers,
    )
    replay = client.post(
        f"/api/v1/interview/{interview_id}/answer",
        json=answer,
        headers=candidate_headers,
    )
    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert client.post(
        f"/api/v1/interview/{interview_id}/report", headers=candidate_headers
    ).status_code == 200
    assert client.get(
        f"/api/v1/interview/{interview_id}",
        headers=other_recruiter_headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/interview/{interview_id}/report",
        headers=other_recruiter_headers,
    ).status_code == 404

    candidate_token = candidate_headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(
        f"/ws/interview/{interview_id}?token={candidate_token}"
    ) as websocket:
        assert websocket.receive_json()["type"] == "connected"

    with SessionLocal() as session:
        actions = set(
            session.execute(
                select(AccessAuditRecord.action, AccessAuditRecord.resource_type)
                .where(
                    AccessAuditRecord.actor_user_id.in_(
                        [admin["id"], candidate_user["id"]]
                    )
                )
            ).all()
        )
    assert ("verify_email_out_of_band", "user") in actions
    assert ("link", "candidate") in actions

    reused = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": token},
        headers=candidate_headers,
    )
    assert reused.status_code == 400
    assert invitation["token"] not in str(stored.token_hash)


def test_invitation_requires_owned_profile_and_verified_account(
    client: TestClient,
):
    recruiter, recruiter_headers = create_user("recruiter")
    _, other_headers = create_user("recruiter")
    candidate_user, _ = create_user("candidate")
    admin, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, candidate_user["email"])

    assert create_invitation(client, other_headers, profile["id"]).status_code == 404
    not_verified = create_invitation(client, recruiter_headers, profile["id"])
    assert not_verified.status_code == 409

    denied_verification = verify_email(
        client,
        other_headers,
        candidate_user["id"],
    )
    assert denied_verification.status_code == 403
    assert verify_email(client, admin_headers, candidate_user["id"]).status_code == 200
    assert create_invitation(
        client, recruiter_headers, profile["id"]
    ).status_code == 201

    with SessionLocal() as session:
        verification_audit = session.execute(
            select(AccessAuditRecord).where(
                AccessAuditRecord.actor_user_id == admin["id"],
                AccessAuditRecord.action == "verify_email_out_of_band",
                AccessAuditRecord.resource_id == candidate_user["id"],
            )
        ).scalar_one()
    assert verification_audit.resource_type == "user"
    assert recruiter["id"] != admin["id"]


def test_public_signup_cannot_assign_privileged_role(client: TestClient):
    email = f"public-role-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret123", "role": "admin"},
    )
    assert response.status_code == 200
    user = UserStore.get_by_email(email)
    assert user is not None
    assert user["role"] == "candidate"
    with SessionLocal() as session:
        record = session.execute(
            select(UserRecord).where(UserRecord.email == email)
        ).scalar_one()
        assert record.email_verified_at is None


@pytest.mark.parametrize("invalid_token", ["x", token_urlsafe(32)])
def test_malformed_and_unknown_tokens_have_safe_response(
    client: TestClient, invalid_token: str
):
    _, headers = create_user("candidate")
    response = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invalid_token},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invitation is invalid or unavailable"


def test_email_mismatch_unverified_and_expired_invitations_are_rejected(
    client: TestClient,
):
    recruiter, recruiter_headers = create_user("recruiter")
    target_user, target_headers = create_user("candidate")
    other_user, other_headers = create_user("candidate")
    admin, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, target_user["email"])
    assert verify_email(client, admin_headers, target_user["id"]).status_code == 200
    assert verify_email(client, admin_headers, other_user["id"]).status_code == 200

    invitation = create_invitation(client, recruiter_headers, profile["id"]).json()
    mismatch = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=other_headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "Invitation is invalid or unavailable"

    with SessionLocal.begin() as session:
        session.execute(
            update(UserRecord)
            .where(UserRecord.id == target_user["id"])
            .values(email_verified_at=None)
        )
    unverified = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=target_headers,
    )
    assert unverified.status_code == 400

    with SessionLocal.begin() as session:
        session.execute(
            update(UserRecord)
            .where(UserRecord.id == target_user["id"])
            .values(email_verified_at=datetime.now(UTC))
        )
        session.execute(
            update(CandidateInvitationRecord)
            .where(CandidateInvitationRecord.id == invitation["invitation_id"])
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    expired = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=target_headers,
    )
    assert expired.status_code == 400
    assert recruiter["id"] != admin["id"]


def test_revoked_invitation_cannot_be_redeemed(client: TestClient):
    _, recruiter_headers = create_user("recruiter")
    candidate_user, candidate_headers = create_user("candidate")
    admin, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, candidate_user["email"])
    assert verify_email(client, admin_headers, candidate_user["id"]).status_code == 200
    invitation = create_invitation(client, recruiter_headers, profile["id"]).json()
    revoked = client.delete(
        f"/api/v1/candidates/{profile['id']}/invitations",
        headers=recruiter_headers,
    )
    assert revoked.status_code == 200, revoked.text

    redemption = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=candidate_headers,
    )
    assert redemption.status_code == 400
    with SessionLocal() as session:
        audit = session.execute(
            select(AccessAuditRecord).where(
                AccessAuditRecord.actor_user_id == admin["id"],
                AccessAuditRecord.action == "verify_email_out_of_band",
            )
        ).scalar_one()
        stored = session.get(
            CandidateInvitationRecord, invitation["invitation_id"]
        )
        assert audit.resource_id == candidate_user["id"]
        assert stored is not None
        assert stored.revoked_at is not None


def test_two_candidate_accounts_cannot_claim_one_profile(client: TestClient):
    _, recruiter_headers = create_user("recruiter")
    intended_user, intended_headers = create_user("candidate")
    other_user, other_headers = create_user("candidate")
    _, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, intended_user["email"])
    assert verify_email(client, admin_headers, intended_user["id"]).status_code == 200
    assert verify_email(client, admin_headers, other_user["id"]).status_code == 200
    invitation = create_invitation(client, recruiter_headers, profile["id"]).json()

    wrong_user = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=other_headers,
    )
    assert wrong_user.status_code == 400
    claimed = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": invitation["token"]},
        headers=intended_headers,
    )
    assert claimed.status_code == 200
    assert intended_user["id"] != other_user["id"]


def test_simultaneous_redemption_links_exactly_once(client: TestClient):
    _, recruiter_headers = create_user("recruiter")
    candidate_user, candidate_headers = create_user("candidate")
    _, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, candidate_user["email"])
    assert verify_email(client, admin_headers, candidate_user["id"]).status_code == 200
    invitation = create_invitation(client, recruiter_headers, profile["id"]).json()

    def redeem():
        return client.post(
            "/api/v1/candidate-invitations/redeem",
            json={"token": invitation["token"]},
            headers=candidate_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: redeem(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 400]
    with SessionLocal() as session:
        linked = session.get(CandidateRecord, profile["id"])
        stored = session.get(
            CandidateInvitationRecord, invitation["invitation_id"]
        )
        assert linked is not None
        assert linked.user_id == candidate_user["id"]
        assert stored is not None
        assert stored.consumed_at is not None


def test_candidate_account_link_uniqueness_blocks_second_profile():
    first_user, _ = create_user("candidate")
    recruiter, _ = create_user("recruiter")
    first_profile = CandidateRecord(
        name="First",
        email=f"first-{uuid4()}@example.com",
        owner_user_id=recruiter["id"],
        user_id=first_user["id"],
    )
    second_profile = CandidateRecord(
        name="Second",
        email=f"second-{uuid4()}@example.com",
        owner_user_id=recruiter["id"],
    )
    with SessionLocal.begin() as session:
        session.add_all([first_profile, second_profile])
    with pytest.raises(IntegrityError), SessionLocal.begin() as session:
        session.execute(
            update(CandidateRecord)
            .where(CandidateRecord.id == second_profile.id)
            .values(user_id=first_user["id"])
        )
    with SessionLocal() as session:
        assert session.get(CandidateRecord, second_profile.id).user_id is None


def test_invitation_creation_and_redemption_are_rate_limited(
    client: TestClient,
):
    _, recruiter_headers = create_user("recruiter")
    candidate_user, candidate_headers = create_user("candidate")
    _, admin_headers = create_user("admin")
    profile = create_candidate(client, recruiter_headers, candidate_user["email"])
    assert verify_email(client, admin_headers, candidate_user["id"]).status_code == 200

    created = create_invitation(client, recruiter_headers, profile["id"])
    assert created.status_code == 201, created.text
    limited_creation = create_invitation(
        client, recruiter_headers, profile["id"]
    )
    assert limited_creation.status_code == 429

    _, unverified_headers = create_user("candidate")
    for _ in range(20):
        response = client.post(
            "/api/v1/candidate-invitations/redeem",
            json={"token": token_urlsafe(32)},
            headers=unverified_headers,
        )
        assert response.status_code == 400
    limited_redemption = client.post(
        "/api/v1/candidate-invitations/redeem",
        json={"token": token_urlsafe(32)},
        headers=unverified_headers,
    )
    assert limited_redemption.status_code == 429
