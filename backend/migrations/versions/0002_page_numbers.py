"""add page_start and page_end to document_chunks

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("page_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_chunks", "page_end")
    op.drop_column("document_chunks", "page_start")
