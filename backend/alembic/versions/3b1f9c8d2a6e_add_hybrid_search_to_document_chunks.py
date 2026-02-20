"""add hybrid search to document_chunks

Revision ID: 3b1f9c8d2a6e
Revises: 280e15765d80
Create Date: 2026-02-19 22:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3b1f9c8d2a6e'
down_revision: Union[str, None] = '280e15765d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the search_vector column with GENERATED ALWAYS AS (to_tsvector(...))
    op.execute("""
        ALTER TABLE document_chunks 
        ADD COLUMN search_vector tsvector 
        GENERATED ALWAYS AS (
            to_tsvector('portuguese', coalesce(content, ''))
        ) STORED;
    """)

    # Create the GIN index for fast full-text search
    op.create_index(
        'ix_document_chunks_search_vector', 
        'document_chunks', 
        ['search_vector'], 
        unique=False, 
        postgresql_using='gin'
    )


def downgrade() -> None:
    op.drop_index('ix_document_chunks_search_vector', table_name='document_chunks', postgresql_using='gin')
    op.drop_column('document_chunks', 'search_vector')
