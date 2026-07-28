"""resize document chunk embeddings for local Ollama model

Revision ID: 20260728_03
Revises: 20260728_02
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260728_03"
down_revision: str | None = "20260728_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(768) USING NULL::vector(768)"
    )


def downgrade() -> None:
    op.execute("UPDATE document_chunks SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)"
    )
