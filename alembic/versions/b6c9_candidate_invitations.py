"""Add verified email state and single-use candidate invitations."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b6c9_candidate_invitations"
down_revision: str | Sequence[str] | None = "a4d2_resource_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "candidate_invitations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("recruiter_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["recruiter_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_candidate_invitations_candidate_id",
        "candidate_invitations",
        ["candidate_id"],
    )
    op.create_index(
        "ix_candidate_invitations_recruiter_user_id",
        "candidate_invitations",
        ["recruiter_user_id"],
    )
    op.create_index(
        "ix_candidate_invitations_recruiter_created",
        "candidate_invitations",
        ["recruiter_user_id", "created_at"],
    )
    op.create_index(
        "uq_candidate_invitations_one_pending_per_candidate",
        "candidate_invitations",
        ["candidate_id"],
        unique=True,
        sqlite_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"),
        postgresql_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_candidate_invitations_one_pending_per_candidate",
        table_name="candidate_invitations",
    )
    op.drop_index(
        "ix_candidate_invitations_recruiter_created",
        table_name="candidate_invitations",
    )
    op.drop_index(
        "ix_candidate_invitations_recruiter_user_id",
        table_name="candidate_invitations",
    )
    op.drop_index(
        "ix_candidate_invitations_candidate_id",
        table_name="candidate_invitations",
    )
    op.drop_table("candidate_invitations")
    op.drop_column("users", "email_verified_at")
