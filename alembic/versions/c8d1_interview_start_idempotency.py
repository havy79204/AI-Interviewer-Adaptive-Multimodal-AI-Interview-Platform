"""Add idempotent interview-start request tracking."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8d1_interview_start_idempotency"
down_revision: str | Sequence[str] | None = "b6c9_candidate_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("interviews") as batch_op:
        batch_op.add_column(sa.Column("start_request_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("start_request_hash", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("start_request_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("start_request_owner", sa.String(), nullable=True))
    op.create_index(
        "uq_interviews_start_request_key",
        "interviews",
        ["start_request_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_interviews_start_request_key", table_name="interviews")
    with op.batch_alter_table("interviews") as batch_op:
        batch_op.drop_column("start_request_hash")
        batch_op.drop_column("start_request_owner")
        batch_op.drop_column("start_request_status")
        batch_op.drop_column("start_request_key")
