"""Add durable versioned RAG document chunks and embeddings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c31_rag_documents"
down_revision: str | Sequence[str] | None = "8b2f_evidence_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("competency_id", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("language", sa.String(), nullable=False, server_default="en"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("embedding_json", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        sa.Column("embedding_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_id", "version", name="uq_rag_document_chunk_version"),
    )
    op.create_index(
        "ix_rag_document_filters",
        "rag_documents",
        ["active", "job_id", "organization_id", "competency_id", "difficulty"],
    )
    op.create_index(
        "ix_rag_document_embedding_model",
        "rag_documents",
        ["embedding_model", "embedding_dimension"],
    )


def downgrade() -> None:
    op.drop_index("ix_rag_document_embedding_model", table_name="rag_documents")
    op.drop_index("ix_rag_document_filters", table_name="rag_documents")
    op.drop_table("rag_documents")
