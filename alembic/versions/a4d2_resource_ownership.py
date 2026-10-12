"""Add single-tenant resource ownership and privileged-access audit records."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4d2_resource_ownership"
down_revision: str | Sequence[str] | None = "9c31_rag_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default="candidate",
        )
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_candidates_owner_user_id_users", "users", ["owner_user_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_candidates_user_id_users", "users", ["user_id"], ["id"]
        )
        batch_op.create_unique_constraint("uq_candidates_user_id", ["user_id"])
    op.create_index("ix_candidates_owner_user_id", "candidates", ["owner_user_id"])
    op.create_index("ix_candidates_user_id", "candidates", ["user_id"])
    op.create_table(
        "access_audit",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_audit_actor_user_id", "access_audit", ["actor_user_id"])


def downgrade() -> None:
    op.drop_index("ix_access_audit_actor_user_id", table_name="access_audit")
    op.drop_table("access_audit")
    op.drop_index("ix_candidates_user_id", table_name="candidates")
    op.drop_index("ix_candidates_owner_user_id", table_name="candidates")
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_constraint("uq_candidates_user_id", type_="unique")
        batch_op.drop_constraint("fk_candidates_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_candidates_owner_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.drop_column("owner_user_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.String(),
            existing_nullable=False,
            server_default="admin",
        )
