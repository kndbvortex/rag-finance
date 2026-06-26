"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("source_institution", sa.String(255), nullable=False),
        sa.Column("type_document", sa.String(255), nullable=False),
        sa.Column("annee_fiscale", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
        sa.UniqueConstraint("url_hash"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "content_tsv",
            TSVECTOR(),
            sa.Computed("to_tsvector('french', content)", persisted=True),
            nullable=True,
        ),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("contient_tableaux", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_document_chunks_content_tsv",
        "document_chunks",
        ["content_tsv"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding", table_name="document_chunks")
    op.drop_index("ix_document_chunks_content_tsv", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.execute("DROP EXTENSION IF EXISTS vector")
